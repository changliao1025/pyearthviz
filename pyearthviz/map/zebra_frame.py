import itertools

import cartopy.crs as ccrs
import cartopy.mpl.geoaxes
import numpy as np
from matplotlib.patheffects import Normal, Stroke


def _format_coord(val, span, is_lat=False):
    """Format coordinate with hemisphere and adaptive precision based on domain span."""
    if is_lat:
        hemi = "N" if val >= 0 else "S"
    else:
        hemi = "E" if val >= 0 else "W"
    v = abs(val)
    if span >= 5.0:
        return f"{v:.0f}°{hemi}"
    elif span >= 0.5:
        return f"{v:.1f}°{hemi}"
    elif span >= 0.05:
        return f"{v:.2f}°{hemi}"
    elif span >= 0.005:
        return f"{v:.3f}°{hemi}"
    else:
        return f"{v:.4f}°{hemi}"


def zebra_frame(
    self,
    lw=3,
    crs=None,
    zorder=None,
    iFlag_outer_frame_in=None,
    iFlag_label_in=None,
    fontsize_in=None,
    step_label_in=None,
    iFlag_top_label_in=None,
    iFlag_right_label_in=None,
    rotation_y_in=None,
):
    """Draw an alternating black and white zebra border with geographic coordinate labels.

    Parameters
    ----------
    lw : float, optional
        Line width of the zebra border (default 3).
    crs : cartopy.crs.CRS, optional
        Geographic CRS used for coordinate labels. Defaults to PlateCarree().
    zorder : int, optional
        Drawing z-order.
    iFlag_outer_frame_in : int, optional
        Flag to use map bounding box extent for outer frame (default 1).
    iFlag_label_in : int, optional
        Flag to draw longitude/latitude labels outside the zebra frame (default 1).
    fontsize_in : float, optional
        Font size for coordinate labels (default 7).
    step_label_in : int, optional
        Interval step between labeled ticks (default 2, e.g. every 2nd tick).
    iFlag_top_label_in : int, optional
        Whether to draw labels on top border (default 0).
    iFlag_right_label_in : int, optional
        Whether to draw labels on right border (default 0).
    rotation_y_in : float, optional
        Rotation angle for latitude labels (default 90).
    """
    bws = itertools.cycle(["k", "w"])
    self.spines["geo"].set_visible(False)

    geo_crs = crs if crs is not None else ccrs.PlateCarree()
    crs_map = self.projection

    if iFlag_outer_frame_in is not None:
        left, right, bottom, top = self.get_extent()
        xticks = np.arange(left, right + (right - left) / 9, (right - left) / 8)
        yticks = np.arange(bottom, top + (top - bottom) / 9, (top - bottom) / 8)
    else:
        xticks = sorted([*self.get_xticks()])
        xticks = np.unique(np.array(xticks))
        yticks = sorted([*self.get_yticks()])
        yticks = np.unique(np.array(yticks))
        if len(xticks) < 2 or len(yticks) < 2:
            left, right, bottom, top = self.get_extent()
            xticks = np.arange(left, right + (right - left) / 9, (right - left) / 8)
            yticks = np.arange(bottom, top + (top - bottom) / 9, (top - bottom) / 8)
        else:
            left, right = xticks[0], xticks[-1]
            bottom, top = yticks[0], yticks[-1]

    # Draw zebra frame segments
    for ticks, which in zip([xticks, yticks], ["lon", "lat"]):
        for idx, (start, end) in enumerate(zip(ticks, ticks[1:])):
            bw = next(bws)
            if which == "lon":
                xs = [[start, end], [start, end]]
                ys = [[yticks[0], yticks[0]], [yticks[-1], yticks[-1]]]
            else:
                xs = [[xticks[0], xticks[0]], [xticks[-1], xticks[-1]]]
                ys = [[start, end], [start, end]]

            capstyle = "butt" if idx not in (0, len(ticks) - 2) else "projecting"
            for xx, yy in zip(xs, ys):
                self.plot(
                    xx,
                    yy,
                    color=bw,
                    linewidth=max(0, lw - self.spines["geo"].get_linewidth() * 2),
                    clip_on=False,
                    transform=crs_map,
                    zorder=zorder,
                    solid_capstyle=capstyle,
                    path_effects=[
                        Stroke(linewidth=lw, foreground="black"),
                        Normal(),
                    ],
                )

    # Draw coordinate labels
    iFlag_label = 1 if iFlag_label_in is None else int(iFlag_label_in)
    if iFlag_label == 1:
        fontsize = fontsize_in if fontsize_in is not None else 7
        step_label = step_label_in if step_label_in is not None else 2
        rot_y = rotation_y_in if rotation_y_in is not None else 90

        pad_y = (top - bottom) * 0.018
        pad_x = (right - left) * 0.018

        # Compute geographic coordinates at each tick along the border
        lon_vals = []
        for x in xticks:
            try:
                pt = geo_crs.transform_point(x, bottom, crs_map)
                lon_vals.append(pt[0])
            except Exception:
                lon_vals.append(x)

        lat_vals = []
        for y in yticks:
            try:
                pt = geo_crs.transform_point(left, y, crs_map)
                lat_vals.append(pt[1])
            except Exception:
                lat_vals.append(y)

        lon_span = max(lon_vals) - min(lon_vals) if len(lon_vals) > 0 else 1.0
        lat_span = max(lat_vals) - min(lat_vals) if len(lat_vals) > 0 else 1.0

        # Bottom labels (longitude)
        for idx in range(0, len(xticks), step_label):
            sText = _format_coord(lon_vals[idx], lon_span, is_lat=False)
            self.text(
                xticks[idx],
                bottom - pad_y,
                sText,
                transform=crs_map,
                ha="center",
                va="top",
                fontsize=fontsize,
                color="black",
                clip_on=False,
                zorder=zorder if zorder is not None else 20,
            )

        # Left labels (latitude)
        for idx in range(0, len(yticks), step_label):
            # Avoid collision at bottom-left corner if bottom has a label at index 0
            if idx == 0 and 0 in range(0, len(xticks), step_label):
                continue
            # Avoid collision at top-left corner if top has a label at index 0
            if (
                iFlag_top_label_in == 1
                and idx == len(yticks) - 1
                and 0 in range(0, len(xticks), step_label)
            ):
                continue
            sText = _format_coord(lat_vals[idx], lat_span, is_lat=True)
            self.text(
                left - pad_x,
                yticks[idx],
                sText,
                transform=crs_map,
                ha="right",
                va="center",
                fontsize=fontsize,
                color="black",
                rotation=rot_y,
                clip_on=False,
                zorder=zorder if zorder is not None else 20,
            )

        # Optional Top labels
        if iFlag_top_label_in == 1:
            for idx in range(0, len(xticks), step_label):
                sText = _format_coord(lon_vals[idx], lon_span, is_lat=False)
                self.text(
                    xticks[idx],
                    top + pad_y,
                    sText,
                    transform=crs_map,
                    ha="center",
                    va="bottom",
                    fontsize=fontsize,
                    color="black",
                    clip_on=False,
                    zorder=zorder if zorder is not None else 20,
                )

        # Optional Right labels
        if iFlag_right_label_in == 1:
            for idx in range(0, len(yticks), step_label):
                sText = _format_coord(lat_vals[idx], lat_span, is_lat=True)
                self.text(
                    right + pad_x,
                    yticks[idx],
                    sText,
                    transform=crs_map,
                    ha="left",
                    va="center",
                    fontsize=fontsize,
                    color="black",
                    rotation=rot_y,
                    clip_on=False,
                    zorder=zorder if zorder is not None else 20,
                )


setattr(cartopy.mpl.geoaxes.GeoAxes, "zebra_frame", zebra_frame)
