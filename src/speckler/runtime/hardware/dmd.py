import numpy as np

from speckler.config import DMD_HEIGHT, DMD_WIDTH

con = None

def get_connection():
    if con is not None:
        return con
    # establish con
    print("Establishing DMD connection...")
    print("NOT YET IMPLEMENTED")



def send_dmd(dmd_arr: np.typing.NDArray):
    get_connection()
    if dmd_arr.shape[0] is not DMD_WIDTH or dmd_arr.shape[1] is not DMD_HEIGHT:
        print("Invalid arr shape: {}", dmd_arr.shape)
    print("Sending DMD shape...")
    print("NOT YET IMPLEMENTED")