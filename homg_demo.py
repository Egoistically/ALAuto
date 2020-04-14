from util.homg_trans import HomographyTransform as homg
import cv2
import os

if __name__=="__main__":
    color_image = cv2.imread("map.png")
    homg.init_homg_vars()
    homg.load_color_screen(color_image)
    homg.init_map_coordinate()
    homg.create_map()
