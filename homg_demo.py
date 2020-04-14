from util.homg_trans import HomographyTransform as homg
import cv2

if __name__=="__main__":
    color_image = cv2.imread("map.png")
    homg.init_homg_vars()
    homg.load_color_screen(color_image)
    homg.init_map_coordinate()
    homg.create_map()

    p0 = (1,2)
    p1 = homg.map_index_to_coord(p0)
    p2 = homg.inv_transform_coord(p1)
    p3 = homg.transform_coord(p2)
    p4 = homg.coord_to_map_index(p3)

    print(p0)
    print(p1)
    print(p2)
    print(p3)
    print(p4)
