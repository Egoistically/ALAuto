# Image file paths
FREE_TILES_IMG_UP = 'assets/map_detection/free_tile_u.png'
FREE_TILES_IMG_DOWN = 'assets/map_detection/free_tile_d.png'
FREE_TILES_IMG_LEFT = 'assets/map_detection/free_tile_l.png'
FREE_TILES_IMG_RIGHT = 'assets/map_detection/free_tile_r.png'
ARROW_IMG = 'assets/map_detection/persp_arrow.png'
BOSS_IMG = 'assets/map_detection/persp_boss.png'
BOSS_SMALL_IMG = 'assets/map_detection/persp_boss_small.png'
QUESTION_MARK_IMG = 'assets/map_detection/persp_qmark.png'
FREE_TILE_CENTER_IMG = 'assets/map_detection/free_tile_center.png'

# Constants used in the returned map
MAP_OBSTACLE = 0
MAP_FREE = 1
MAP_CHARACTER = 2
MAP_SUPPLY = 3
MAP_ENEMY = 4
MAP_BOSS = 5

# Constants used in the class
TILE_WIDTH = 209
TILE_HEIGHT = 209
MAP_CROP_TOP_LEFT = [185, 240]
MAP_CROP_BOTTOM_RIGHT = [1795, 945]
TRANS_SRC_PTS = [[430, 790], [630, 790], [616, 950], [407, 950]]
TRANS_DST_PTS = [[430, 790], [630, 790], [630, 990], [430, 990]]
CV_CANNY_MIN = 50
CV_CANNY_MAX = 100
CLOSING_KERNEL_MIN_SIZE = 5
CLOSING_KERNEL_MAX_SIZE = 25
CLOSING_KERNEL_INCR_STEP = 5
FREE_TILE_MATCH_THRESH = 0.7
BOUNDARY_RED_LOWER = [160, 70, 240]
BOUNDARY_RED_UPPER = [180, 255, 255]
BOUNDARY_YELLOW_LOWER = [25, 100, 100]
BOUNDARY_YELLOW_UPPER = [35, 255, 255]
BOUNDARY_RED_COUNT_THRESH = 350
BOUNDARY_YELLOW_COUNT_THRESH = 350
BOUNDARY_DETECT_MASK_PERCENTAGE = 0.2
ARROW_MATCH_THRESH = 0.9
FREE_TILE_CENTER_THRESH = 0.9
FREE_TILE_X_OFFSET = -70
FREE_TILE_Y_OFFSET = -70
ARROW_CHARACTER_Y_OFFSET = TILE_HEIGHT * 2.25
BOSS_MATCH_THRESH = 0.9



