"""Script to introspect h5s"""
import glob
import os

import click
import h5py
import matplotlib.pyplot as plt

import home_robot.utils.data_tools.image as image


@click.command()
@click.option("--data-dir", default="./", help="Path where the files are stored")
@click.option(
    "--template",
    default="*.h5",
    help="Files will be looked up using regex: data-dir/template",
)
def main(data_dir, template):
    files = glob.glob(os.path.join(data_dir, template))
    for file in files:
        filename = file.split("/")[-1][:-3]
        h5 = h5py.File(file, "r")
        for g_name in h5:
            print(f"{filename},{g_name}")
            rgb = image.img_from_bytes(h5[g_name]["head_rgb/0"][()])
            print(h5[g_name]["demo_status"][()])
            plt.imshow(rgb)
            plt.show()
            print(h5[g_name].keys())
        h5.close()


if __name__ == "__main__":
    main()
