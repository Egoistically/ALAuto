import cv2
import numpy as np
from util.utils import Utils
import util.homg_trans_consts as trans_consts


class HomographyTransform():
    __top_left_tile_x = None
    __top_left_tile_y = None
    __x_max_index = None
    __y_max_index = None
    __screen = None
    __color_screen = None
    __h_trans_m = None
    __inv_h_trans_m = None
    __h_trans_screen_size = None

    @classmethod
    def init_homg_vars(cls):
        src_pts = np.subtract(trans_consts.TRANS_SRC_PTS, trans_consts.MAP_CROP_TOP_LEFT)
        dst_pts = np.subtract(trans_consts.TRANS_DST_PTS, trans_consts.MAP_CROP_TOP_LEFT)

        # Calculate Homography
        h, status = cv2.findHomography(src_pts, dst_pts)
        diff_arr = np.subtract(trans_consts.MAP_CROP_BUTTOM_RIGHT, trans_consts.MAP_CROP_TOP_LEFT)
        src_w = diff_arr[0]
        src_h = diff_arr[1]
        lin_homg_pts = np.array([
            [0, src_w, src_w, 0],
            [0, 0, src_h, src_h],
            [1, 1, 1, 1]])

        # transform points
        transf_lin_homg_pts = h.dot(lin_homg_pts)
        transf_lin_homg_pts /= transf_lin_homg_pts[2, :]

        # find min and max points
        min_x = np.floor(np.min(transf_lin_homg_pts[0])).astype(int)
        min_y = np.floor(np.min(transf_lin_homg_pts[1])).astype(int)
        max_x = np.ceil(np.max(transf_lin_homg_pts[0])).astype(int)
        max_y = np.ceil(np.max(transf_lin_homg_pts[1])).astype(int)

        # add translation to the transformation matrix to shift to positive values
        anchor_x, anchor_y = 0, 0
        transl_transf = np.eye(3, 3)
        if min_x < 0:
            anchor_x = -min_x
            transl_transf[0, 2] += anchor_x
        if min_y < 0:
            anchor_y = -min_y
            transl_transf[1, 2] += anchor_y
        shifted_transf = transl_transf.dot(h)
        cls.__h_trans_m = shifted_transf / shifted_transf[2, 2]
        cls.__inv_h_trans_m = cv2.invert(shifted_transf)[1]
        cls.__h_trans_screen_size = (anchor_x + max(max_x, src_w), anchor_y + max(max_y, src_h))

    @classmethod
    def load_color_screen(cls, color_screen):
        cls.__color_screen = color_screen
        cls.__screen = cv2.cvtColor(color_screen, cv2.COLOR_BGR2GRAY)

    @classmethod
    def init_map_coordinate(cls):
        # crop the color screen
        free_tile_center = cv2.imread(trans_consts.FREE_TILE_CENTER_IMG, cv2.IMREAD_GRAYSCALE)

        crop_color_screen = cls.__color_screen[:][
                            trans_consts.MAP_CROP_TOP_LEFT[1]:trans_consts.MAP_CROP_BUTTOM_RIGHT[1],
                            trans_consts.MAP_CROP_TOP_LEFT[0]:trans_consts.MAP_CROP_BUTTOM_RIGHT[0]]
        # Warp source image to destination based on homography
        screen_trans = cv2.warpPerspective(crop_color_screen, cls.__h_trans_m, cls.__h_trans_screen_size)
        screen_edge = cv2.Canny(screen_trans, trans_consts.CV_CANNY_MIN, trans_consts.CV_CANNY_MAX)

        closing_kernel = trans_consts.CLOSING_KERNEL_MIN_SIZE
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_kernel, closing_kernel))
        screen_edge_closed = cv2.morphologyEx(screen_edge, cv2.MORPH_CLOSE, kernel)
        res = cv2.matchTemplate(screen_edge_closed, free_tile_center, cv2.TM_CCOEFF_NORMED)
        max_similarity = np.max(res)
        print("free tile center", max_similarity)
        if max_similarity > trans_consts.FREE_TILE_MATCH_THRESH:
            loc = np.where(res == max_similarity)
            point = list(zip(*loc[::-1]))
            x, y = (
                point[0][0] + trans_consts.FREE_TILE_X_OFFSET,
                point[0][1] + trans_consts.FREE_TILE_Y_OFFSET)
        else:
            rects = []
            while len(rects) == 0 and closing_kernel <= trans_consts.CLOSING_KERNEL_MAX_SIZE:
                # try to close the edges
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_kernel, closing_kernel))
                screen_edge_closed = cv2.morphologyEx(screen_edge, cv2.MORPH_CLOSE, kernel)
                trans_contours, _ = cv2.findContours(screen_edge_closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                for cont in trans_contours:
                    # get the convex hull
                    hull = cv2.convexHull(cont)
                    hull = hull.astype(np.float32)
                    # get the bounding rectangle
                    x, y, w, h = cv2.boundingRect(hull)
                    if w * h == 0:
                        continue
                    area_diff = abs(1 - trans_consts.TILE_WIDTH * trans_consts.TILE_HEIGHT / (w * h))
                    if 0.2 > area_diff:
                        # check it's shape is close to a square
                        ratio = abs(1 - w / h)
                        if 0.1 > ratio:
                            rects.append((x, y))
                closing_kernel += trans_consts.CLOSING_KERNEL_INCR_STEP

            if closing_kernel > trans_consts.CLOSING_KERNEL_MAX_SIZE:
                return False

            accum_dist = np.zeros(len(rects))
            for i in range(len(rects)):
                for j in range(len(rects)):
                    if i == j:
                        continue
                    remain_width = abs(rects[i][0] - rects[j][0]) % trans_consts.TILE_WIDTH
                    remain_height = abs(rects[i][1] - rects[j][1]) % trans_consts.TILE_HEIGHT
                    accum_dist[i] += min(trans_consts.TILE_WIDTH - remain_width, remain_width) + min(
                        trans_consts.TILE_HEIGHT - remain_height,
                        remain_height)

            pivot_idx = np.argmin(accum_dist)

            # Calculate how many tiles on the map and the coordinate of top left tile in transformed space
            x, y = rects[pivot_idx]

        cls.__top_left_tile_x = int(x % trans_consts.TILE_WIDTH)
        cls.__top_left_tile_y = int(y % trans_consts.TILE_HEIGHT)
        cls.__y_max_index = int(
            (cls.__h_trans_screen_size[
                 1] - cls.__top_left_tile_y + trans_consts.TILE_HEIGHT - 1) / trans_consts.TILE_HEIGHT)
        cls.__x_max_index = int(
            (cls.__h_trans_screen_size[
                 0] - cls.__top_left_tile_x + trans_consts.TILE_WIDTH - 1) / trans_consts.TILE_WIDTH)

        return True

    @classmethod
    def get_map_shape(cls):
        return (cls.__y_max_index, cls.__x_max_index)

    @classmethod
    def create_map(cls):
        # Read source image.
        free_tile_imgs = []
        free_tile_imgs.append(cv2.imread(trans_consts.FREE_TILES_IMG_UP, cv2.IMREAD_GRAYSCALE))
        free_tile_imgs.append(cv2.imread(trans_consts.FREE_TILES_IMG_DOWN, cv2.IMREAD_GRAYSCALE))
        free_tile_imgs.append(cv2.imread(trans_consts.FREE_TILES_IMG_LEFT, cv2.IMREAD_GRAYSCALE))
        free_tile_imgs.append(cv2.imread(trans_consts.FREE_TILES_IMG_RIGHT, cv2.IMREAD_GRAYSCALE))

        # crop the color screen
        crop_color_screen = cls.__color_screen[:][
                            trans_consts.MAP_CROP_TOP_LEFT[1]:trans_consts.MAP_CROP_BUTTOM_RIGHT[1],
                            trans_consts.MAP_CROP_TOP_LEFT[0]:trans_consts.MAP_CROP_BUTTOM_RIGHT[0]]
        # Warp source image to destination based on homography
        screen_trans = cv2.warpPerspective(crop_color_screen, cls.__h_trans_m, cls.__h_trans_screen_size)
        screen_edge = cv2.Canny(screen_trans, trans_consts.CV_CANNY_MIN, trans_consts.CV_CANNY_MAX)

        closing_kernel = trans_consts.CLOSING_KERNEL_MIN_SIZE
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_kernel, closing_kernel))
        screen_edge_closed = cv2.morphologyEx(screen_edge, cv2.MORPH_CLOSE, kernel)

        x_max_index = cls.__x_max_index
        y_max_index = cls.__y_max_index

        battle_map = np.zeros(shape=(y_max_index, x_max_index))

        for i in range(x_max_index):
            for j in range(y_max_index):
                cur_x = cls.__top_left_tile_x + i * trans_consts.TILE_WIDTH
                cur_y = cls.__top_left_tile_y + j * trans_consts.TILE_HEIGHT
                crop = screen_edge_closed[cur_y: cur_y + trans_consts.TILE_HEIGHT,
                       cur_x:cur_x + trans_consts.TILE_WIDTH]
                # Get the coordinate of the center of a tile in the original space
                # For debugging only
                dot = np.array(
                    [[[cur_x + trans_consts.TILE_WIDTH / 2, cur_y + trans_consts.TILE_HEIGHT / 2]]])
                dot = cv2.perspectiveTransform(dot, cls.__inv_h_trans_m)
                dot = dot.astype(int)
                counter = 0
                for safe_tile in free_tile_imgs:
                    if crop.shape[0] >= safe_tile.shape[0] and crop.shape[1] >= safe_tile.shape[1]:
                        res = cv2.matchTemplate(crop, safe_tile, cv2.TM_CCOEFF_NORMED)
                        if np.count_nonzero(res >= trans_consts.FREE_TILE_MATCH_THRESH) > 0:
                            counter += 1
                if counter >= 1:
                    battle_map[j, i] = trans_consts.FREE
                    # For debugging only
                    cv2.circle(crop_color_screen, tuple(dot[0][0]), 3, (0, 255, 0), thickness=3)

                # crop the perspective transformed color screen
                color_crop = screen_trans[cur_y: cur_y + trans_consts.TILE_HEIGHT,
                             cur_x:cur_x + trans_consts.TILE_WIDTH]
                if color_crop.shape < (trans_consts.TILE_HEIGHT * 0.8, trans_consts.TILE_WIDTH * 0.8):
                    continue
                hor_bound_width = int(trans_consts.TILE_HEIGHT * trans_consts.BOUNDARY_DETECT_MASK_PERCENTAGE)
                ver_bound_width = int(trans_consts.TILE_WIDTH * trans_consts.BOUNDARY_DETECT_MASK_PERCENTAGE)
                mask = np.zeros(color_crop.shape[:2], dtype=np.uint8)
                mask[:, :hor_bound_width] = 255  # up
                mask[:, -hor_bound_width:] = 255  # down
                mask[:ver_bound_width, :] = 255  # left
                mask[-ver_bound_width:, :] = 255  # right
                color_crop = cv2.bitwise_and(color_crop, color_crop, mask=mask)
                hsv_crop = cv2.cvtColor(color_crop, cv2.COLOR_BGR2HSV)
                # detect red and yellow boundaries
                lower_red = np.array(trans_consts.BOUNDARY_RED_LOWER)
                upper_red = np.array(trans_consts.BOUNDARY_RED_UPPER)
                lower_yellow = np.array(trans_consts.BOUNDARY_YELLOW_LOWER)
                upper_yellow = np.array(trans_consts.BOUNDARY_YELLOW_UPPER)
                red_hsv_color_mask = cv2.inRange(hsv_crop, lower_red, upper_red)
                yellow_hsv_color_mask = cv2.inRange(hsv_crop, lower_yellow, upper_yellow)
                if np.count_nonzero(red_hsv_color_mask) > trans_consts.BOUNDARY_RED_COUNT_THRESH:
                    battle_map[j, i] = trans_consts.ENEMY
                    # for debugging
                    cv2.circle(crop_color_screen, tuple(dot[0][0]), 3, (0, 0, 255), thickness=3)

                elif np.count_nonzero(yellow_hsv_color_mask) > trans_consts.BOUNDARY_YELLOW_COUNT_THRESH:
                    battle_map[j, i] = trans_consts.SUPPLY
                    #  for debugging
                    cv2.circle(crop_color_screen, tuple(dot[0][0]), 3, (0, 255, 255), thickness=3)

        for i in range(x_max_index):
            for j in range(y_max_index):
                # Draw the boundary of the tile on the original screen.
                # for debugging
                cur_x = cls.__top_left_tile_x + i * trans_consts.TILE_WIDTH
                cur_y = cls.__top_left_tile_y + j * trans_consts.TILE_HEIGHT
                rect = np.array(
                    [[[cur_x, cur_y]], [[cur_x + trans_consts.TILE_WIDTH, cur_y]],
                     [[cur_x + trans_consts.TILE_WIDTH, cur_y + trans_consts.TILE_HEIGHT]],
                     [[cur_x, cur_y + trans_consts.TILE_HEIGHT]]],
                    dtype=np.float64)
                rect = cv2.perspectiveTransform(rect, cls.__inv_h_trans_m)
                rect = rect.astype(int)
                cv2.drawContours(crop_color_screen, [rect], -1, (255, 0, 0), 3)

        cls.__match_boss(screen_trans, battle_map)
        cls.__match_character(screen_trans, battle_map)
        # for debugging
        cv2.imwrite("debug_color_trans.png", screen_trans)
        cv2.imwrite("debug_edge.png", screen_edge_closed)
        cv2.imwrite("debug_color.png", crop_color_screen)
        print(battle_map)

        return battle_map

    @classmethod
    def __match_boss(cls, screen_trans, battle_map):
        if Utils.small_boss_icon:
            boss = cv2.imread(trans_consts.BOSS_SMALL_IMG)
        else:
            boss = cv2.imread(trans_consts.BOSS_IMG)
        res = cv2.matchTemplate(screen_trans, boss, cv2.TM_CCOEFF_NORMED)
        max_similarity = np.max(res)
        print("boss", max_similarity)
        if max_similarity > trans_consts.BOSS_MATCH_THRESH:
            loc = np.where(res == max_similarity)
            point = list(zip(*loc[::-1]))
            if len(point) > 0:
                # Calculate x and y of the tile where the boos is
                x, y = cls.coord_to_battle_map_index((point[0][0], point[0][1]))
                if 0 <= x < battle_map.shape[1] and 0 <= y < battle_map.shape[0]:
                    battle_map[y, x] = trans_consts.BOSS

    @classmethod
    def __match_character(cls, screen_trans, battle_map):
        arrow = cv2.imread(trans_consts.ARROW_IMG)
        res = cv2.matchTemplate(screen_trans, arrow, cv2.TM_CCOEFF_NORMED)
        max_similarity = np.max(res)
        print("arrow", max_similarity)
        if max_similarity > trans_consts.ARROW_MATCH_THRESH:
            loc = np.where(res == max_similarity)
            point = list(zip(*loc[::-1]))
            if len(point) > 0:
                # Calculate x and y of the tile where the character is
                # add a y offset due to the arrow is above the character
                x, y = cls.coord_to_battle_map_index(
                    (point[0][0], point[0][1] + trans_consts.ARROW_CHARACTER_Y_OFFSET))
                if 0 <= x < battle_map.shape[1] and 0 <= y < battle_map.shape[0]:
                    battle_map[y, x] = trans_consts.CHARACTER

    @classmethod
    def coord_to_battle_map_index(cls, coord):
        x = int((coord[0] - cls.__top_left_tile_x) / trans_consts.TILE_WIDTH)
        y = int((coord[1] - cls.__top_left_tile_y) / trans_consts.TILE_HEIGHT)
        return x, y

    @classmethod
    def battle_map_index_to_coord(cls, index):
        x = cls.__top_left_tile_x + index[1] * trans_consts.TILE_WIDTH + trans_consts.TILE_WIDTH / 2
        y = cls.__top_left_tile_y + index[0] * trans_consts.TILE_HEIGHT + trans_consts.TILE_HEIGHT / 2
        return x, y

    @classmethod
    def bfs_search(cls, battle_map, start_tile):
        if start_tile[0] < 0 or start_tile[0] >= battle_map.shape[0] or start_tile[1] < 0 or start_tile[1] >= \
                battle_map.shape[1]:
            return [], []

        pad_map = np.zeros(shape=(battle_map.shape[0] + 2, battle_map.shape[1] + 2))
        pad_map[1:battle_map.shape[0] + 1, 1:battle_map.shape[1] + 1] = battle_map[:, :]
        visited_map = np.zeros(shape=pad_map.shape)
        queue = []
        found_enemies = []
        found_supplies = []

        cur = (start_tile[0] + 1, start_tile[1] + 1)
        queue.append(cur)
        visited_map[cur] = -1
        while len(queue) > 0:
            new_queue = []
            for cur in queue:
                next_locs = [(cur[0] - 1, cur[1]), (cur[0] + 1, cur[1]), (cur[0], cur[1] - 1), (cur[0], cur[1] + 1)]
                for i in range(4):
                    loc = next_locs[i]
                    if visited_map[loc] == 0:
                        visited_map[loc] = i + 1
                        if pad_map[loc] == trans_consts.ENEMY or pad_map[loc] == trans_consts.BOSS:
                            found_enemies.append((loc[0] - 1, loc[1] - 1))
                        elif pad_map[loc] == trans_consts.SUPPLY:
                            found_supplies.append((loc[0] - 1, loc[1] - 1))
                        elif pad_map[loc] == trans_consts.FREE or pad_map[loc] == trans_consts.CHARACTER:
                            new_queue.append(loc)
            queue = new_queue
        return found_enemies, found_supplies
