import numpy as np
import skimage.measure
import skimage.segmentation
import skimage.morphology
import skimage.filters
import scipy.ndimage


def segment_HU_scan_ira(x, threshold=-350, min_area=1000000):
    mask = np.asarray(x < threshold, dtype='int8')

    mask = skimage.morphology.binary_opening(mask, skimage.morphology.cube(4))
    mask = np.asarray(mask, dtype='int8')

    for zi in xrange(mask.shape[0]):
        skimage.segmentation.clear_border(mask[zi, :, :], in_place=True)

    label_image = skimage.measure.label(mask)
    region_props = skimage.measure.regionprops(label_image)
    sorted_regions = sorted(region_props, key=lambda x: x.area, reverse=True)
    lung_region = sorted_regions[0]
    n_lung_regions = 1
    candidate_lung_regions = []
    for r in sorted_regions:
        if r.area > min_area:
            candidate_lung_regions.append(r)
    if len(candidate_lung_regions) > 1:
        print 'NUMBER OF CANDIDATE REGIONS', len(candidate_lung_regions)
        middle_patch = label_image[mask.shape[0] / 2]
        region2distance, region2centroid = {}, {}
        for r in candidate_lung_regions:
            middle_patch_r = middle_patch == r.label
            centroid = np.average(np.where(middle_patch_r), axis=1)
            region2centroid[r] = centroid
            distance = np.sum((centroid - np.asarray(middle_patch.shape) / 2) ** 2)
            region2distance[r] = distance
        lung_region = min(region2distance, key=region2distance.get)
        for r in candidate_lung_regions:
            print region2centroid[r]
            if abs(region2centroid[r][0] - region2centroid[lung_region][0]) < 100:
                label_image[label_image == r.label] = lung_region.label
                n_lung_regions += 1

    lung_label = lung_region.label
    lung_mask = np.asarray((label_image == lung_label), dtype='int8')

    # convex hull mask
    lung_mask_convex = np.zeros_like(lung_mask)
    for i in range(lung_mask.shape[2]):
        if np.any(lung_mask[:, :, i]):
            lung_mask_convex[:, :, i] = skimage.morphology.convex_hull_image(lung_mask[:, :, i])

    # old mask inside the convex hull
    mask *= lung_mask_convex
    label_image = skimage.measure.label(mask)
    region_props = skimage.measure.regionprops(label_image)
    sorted_regions = sorted(region_props, key=lambda x: x.area, reverse=True)

    for r in sorted_regions[n_lung_regions:]:
        if r.area > 125:
            label_image_r = label_image == r.label
            for i in range(label_image_r.shape[0]):
                if np.any(label_image_r[i]):
                    label_image_r[i] = skimage.morphology.convex_hull_image(label_image_r[i])
            lung_mask_convex *= 1 - label_image_r

    return lung_mask_convex
