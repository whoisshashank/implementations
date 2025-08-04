import roma
import torch
import torch.nn as nn
import torch.nn.functional as F
from gsplat.rendering import rasterization
from gsplat.rendering import rasterization_2dgs
from torch import Tensor

from flow3d.params import GaussianParams, MotionBases, CameraScales, CameraPoses


class SceneModel(nn.Module):
    def __init__(
        self,
        Ks: Tensor,
        w2cs: Tensor,
        fg_params: GaussianParams,
        motion_bases: MotionBases,
        camera_poses: CameraPoses | None = None,
        bg_params: GaussianParams | None = None,
        use_2dgs: bool = False,
    ):
        super().__init__()
        self.num_frames = motion_bases.num_frames
        self.fg = fg_params
        self.motion_bases = motion_bases
        self.bg = bg_params
        scene_scale = 1.0 if bg_params is None else bg_params.scene_scale
        self.register_buffer("bg_scene_scale", torch.as_tensor(scene_scale))
        self.register_buffer("Ks", Ks)
        self.register_buffer("w2cs", w2cs)
        self.camera_poses = camera_poses

        self._current_xys = None
        self._current_radii = None
        self._current_img_wh = None

        self.use_2dgs = use_2dgs

    @property
    def num_gaussians(self) -> int:
        return self.num_bg_gaussians + self.num_fg_gaussians

    @property
    def num_bg_gaussians(self) -> int:
        return self.bg.num_gaussians if self.bg is not None else 0

    @property
    def num_fg_gaussians(self) -> int:
        return self.fg.num_gaussians

    @property
    def num_motion_bases(self) -> int:
        return self.motion_bases.num_bases

    @property
    def has_bg(self) -> bool:
        return self.bg is not None

    def compute_poses_bg(self) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            means: (G, B, 3)
            quats: (G, B, 4)
        """
        assert self.bg is not None
        return self.bg.params["means"], self.bg.get_quats()

    def compute_transforms(
        self, ts: torch.Tensor, inds: torch.Tensor | None = None
    ) -> torch.Tensor:
        coefs = self.fg.get_coefs()  # (G, K)
        if inds is not None:
            coefs = coefs[inds]
        transfms = self.motion_bases.compute_transforms(ts, coefs)  # (G, B, 3, 4)
        return transfms

    def compute_poses_fg(
        self, ts: torch.Tensor | None, inds: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        :returns means: (G, B, 3), quats: (G, B, 4)
        """
        means = self.fg.params["means"]  # (G, 3)
        quats = self.fg.get_quats()  # (G, 4)
        if inds is not None:
            means = means[inds]
            quats = quats[inds]
        if ts is not None:
            transfms = self.compute_transforms(ts, inds)  # (G, B, 3, 4)
            means = torch.einsum(
                "pnij,pj->pni",
                transfms,
                F.pad(means, (0, 1), value=1.0),
            )
            quats = roma.quat_xyzw_to_wxyz(
                (
                    roma.quat_product(
                        roma.rotmat_to_unitquat(transfms[..., :3, :3]),
                        roma.quat_wxyz_to_xyzw(quats[:, None]),
                    )
                )
            )
            quats = F.normalize(quats, p=2, dim=-1)
        else:
            means = means[:, None]
            quats = quats[:, None]
        return means, quats

    def compute_poses_all(
        self, ts: torch.Tensor | None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        means, quats = self.compute_poses_fg(ts)
        if self.has_bg:
            bg_means, bg_quats = self.compute_poses_bg()
            means = torch.cat(
                [means, bg_means[:, None].expand(-1, means.shape[1], -1)], dim=0
            ).contiguous()
            quats = torch.cat(
                [quats, bg_quats[:, None].expand(-1, means.shape[1], -1)], dim=0
            ).contiguous()
        return means, quats

    def get_colors_all(self) -> torch.Tensor:
        colors = self.fg.get_colors()
        if self.bg is not None:
            colors = torch.cat([colors, self.bg.get_colors()], dim=0).contiguous()
        return colors

    def get_scales_all(self) -> torch.Tensor:
        scales = self.fg.get_scales()
        if self.bg is not None:
            scales = torch.cat([scales, self.bg.get_scales()], dim=0).contiguous()
        return scales

    def get_opacities_all(self) -> torch.Tensor:
        """
        :returns colors: (G, 3), scales: (G, 3), opacities: (G, 1)
        """
        opacities = self.fg.get_opacities()
        if self.bg is not None:
            opacities = torch.cat(
                [opacities, self.bg.get_opacities()], dim=0
            ).contiguous()
        return opacities

    @staticmethod
    def init_from_state_dict(state_dict, prefix=""):
        fg = GaussianParams.init_from_state_dict(
            state_dict, prefix=f"{prefix}fg.params."
        )
        bg = None
        if any("bg." in k for k in state_dict):
            bg = GaussianParams.init_from_state_dict(
                state_dict, prefix=f"{prefix}bg.params."
            )
        motion_bases = MotionBases.init_from_state_dict(
            state_dict, prefix=f"{prefix}motion_bases.params."
        )
        Ks = state_dict[f"{prefix}Ks"]
        w2cs = state_dict[f"{prefix}w2cs"]
        camera_poses = None
        if any("camera_poses." in k for k in state_dict):
            camera_poses = CameraPoses.init_from_state_dict(
                state_dict, prefix=f"{prefix}camera_poses.params."
            )

        return SceneModel(
            Ks, 
            w2cs, 
            fg, 
            motion_bases, 
            camera_poses,
            bg
        )

    def render(
        self,
        # A single time instance for view rendering.
        t: int | None,
        w2cs: torch.Tensor,  # (C, 4, 4)
        Ks: torch.Tensor,  # (C, 3, 3)
        img_wh: tuple[int, int],
        # Multiple time instances for track rendering: (B,).
        target_ts: torch.Tensor | None = None,  # (B)
        target_w2cs: torch.Tensor | None = None,  # (B, 4, 4)
        bg_color: torch.Tensor | float = 1.0,
        colors_override: torch.Tensor | None = None,
        means: torch.Tensor | None = None,
        quats: torch.Tensor | None = None,
        target_means: torch.Tensor | None = None,
        return_color: bool = True,
        return_depth: bool = False,
        return_mask: bool = False,
        fg_only: bool = False,
        filter_mask: torch.Tensor | None = None,
    ) -> dict:

        curr_w2cs = w2cs

        if target_w2cs is not None:
            target_w2cs_clone = target_w2cs
        device = w2cs.device
        C = w2cs.shape[0]

        W, H = img_wh
        pose_fnc = self.compute_poses_fg if fg_only else self.compute_poses_all
        N = self.num_fg_gaussians if fg_only else self.num_gaussians

        if means is None or quats is None:
            means, quats = pose_fnc(
                torch.tensor([t], device=device) if t is not None else None
            )
            means = means[:, 0]
            quats = quats[:, 0]

        if colors_override is None:
            if return_color:
                colors_override = (
                    self.fg.get_colors() if fg_only else self.get_colors_all()
                )
            else:
                colors_override = torch.zeros(N, 0, device=device)

        D = colors_override.shape[-1]

        scales = self.fg.get_scales() if fg_only else self.get_scales_all()
        opacities = self.fg.get_opacities() if fg_only else self.get_opacities_all()

        if isinstance(bg_color, float):
            bg_color = torch.full((C, D), bg_color, device=device)
        assert isinstance(bg_color, torch.Tensor)

        mode = "RGB"
        ds_expected = {"img": D}

        if return_mask:
            if self.has_bg and not fg_only:
                mask_values = torch.zeros((self.num_gaussians, 1), device=device)
                mask_values[: self.num_fg_gaussians] = 1.0
            else:
                mask_values = torch.ones((self.num_fg_gaussians, 1), device=device)
            colors_override = torch.cat([colors_override, mask_values], dim=-1)
            bg_color = torch.cat([bg_color, torch.zeros(C, 1, device=device)], dim=-1)
            ds_expected["mask"] = 1

        B = 0
        if target_ts is not None:
            B = target_ts.shape[0]
            if target_means is None:
                target_means, _ = pose_fnc(target_ts)  # [G, B, 3]
            if target_w2cs_clone is not None:
                target_means = torch.einsum(
                    "bij,pbj->pbi",
                    target_w2cs_clone[:, :3],
                    F.pad(target_means, (0, 1), value=1.0),
                )
            track_3d_vals = target_means.flatten(-2)  # (G, B * 3)
            d_track = track_3d_vals.shape[-1]
            colors_override = torch.cat([colors_override, track_3d_vals], dim=-1)
            bg_color = torch.cat(
                [bg_color, torch.zeros(C, track_3d_vals.shape[-1], device=device)],
                dim=-1,
            )
            ds_expected["tracks_3d"] = d_track

        assert colors_override.shape[-1] == sum(ds_expected.values())
        assert bg_color.shape[-1] == sum(ds_expected.values())

        if return_depth:
            mode = "RGB+ED"
            ds_expected["depth"] = 1

        if filter_mask is not None:
            assert filter_mask.shape == (N,)
            means = means[filter_mask]
            quats = quats[filter_mask]
            scales = scales[filter_mask]
            opacities = opacities[filter_mask]
            colors_override = colors_override[filter_mask]

        if self.camera_poses is not None:
            w2cs = self.camera_poses.get_camera_matrix()
            w2cs = w2cs[t].unsqueeze(0)

        if self.use_2dgs:
            colors_override = torch.nan_to_num(colors_override, nan=1e-6)
            backgrounds = torch.nan_to_num(bg_color, nan=1.0)

            outputs = rasterization_2dgs(
                means=means,
                quats=quats,
                scales=scales,
                opacities=opacities,
                colors=colors_override,
                backgrounds=bg_color,
                viewmats=curr_w2cs,  # [C, 4, 4]
                Ks=Ks,  # [C, 3, 3]
                width=W,
                height=H,
                packed=False,
                render_mode=mode,
            )

            (
                render_colors,
                alphas,
                render_normals,
                surf_normals,
                _,
                _,
                info,
            ) = outputs
        
        else:
            render_colors, alphas, info = rasterization(
                means=means,
                quats=quats,
                scales=scales,
                opacities=opacities,
                colors=colors_override,
                backgrounds=bg_color,
                viewmats=curr_w2cs,  # [C, 4, 4]
                Ks=Ks,  # [C, 3, 3]
                width=W,
                height=H,
                packed=False,
                render_mode=mode,
            )
            render_normals = None
            surf_normals = None

        # Populate the current data for adaptive gaussian control.
        if self.training and info["means2d"].requires_grad:
            self._current_xys = info["means2d"]
            self._current_radii = info["radii"]
            self._current_img_wh = img_wh
            # We want to be able to access to xys' gradients later in a
            # torch.no_grad context.
            self._current_xys.retain_grad()

        assert render_colors.shape[-1] == sum(ds_expected.values())
        outputs = torch.split(render_colors, list(ds_expected.values()), dim=-1)
        out_dict = {}
        for i, (name, dim) in enumerate(ds_expected.items()):
            x = outputs[i]
            assert x.shape[-1] == dim, f"{x.shape[-1]=} != {dim=}"
            if name == "tracks_3d":
                x = x.reshape(C, H, W, B, 3)
            out_dict[name] = x
        out_dict["acc"] = alphas
        out_dict["rend_normal"] = render_normals
        out_dict["surf_normal"] = surf_normals
        return out_dict
