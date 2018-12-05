#!/usr/bin/env python3

import argparse
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from keras.models import load_model

import filename_loaders
import train
# import plot


def averaged_prediction(predictions, stack_size, idx):
    pred = 0.0
    for j in range(stack_size):
        for k in range(j, stack_size):
            pred += predictions[idx+j] / (stack_size * (k+1))
    return pred


def calc_poses(predictions, stamps, stack_size):

    poses = []

    curr_pos = [0, 0]
    positions = [[0, 0]]
    yaw_global = np.deg2rad(0.0)

    for i, prediction in enumerate(predictions[:-stack_size]):

        duration = stamps[i+1] - stamps[i]
        duration_total = stamps[i+stack_size-1] - stamps[i]

        prediction = averaged_prediction(predictions, stack_size, i)
        vel_y, vel_x, vel_yaw = prediction / duration_total

        trans_local = np.array([vel_y * duration, vel_x * duration])
        yaw_local = vel_yaw * duration

        rot = np.array([
            [np.sin(yaw_global),  np.cos(yaw_global)],
            [np.cos(yaw_global), -np.sin(yaw_global)]
        ])

        trans_global = rot.dot(trans_local)
        curr_pos += trans_global

        yaw_global = (yaw_global + yaw_local) % (2 * np.pi)

        pose = np.array([
            [ np.cos(yaw_global), 0, np.sin(yaw_global), curr_pos[0]],
            [                  0, 0,                  0,           0],
            [-np.sin(yaw_global), 0, np.cos(yaw_global), curr_pos[1]]
        ], dtype=np.float32)

        poses.append(pose)

    return poses


def write_poses(output_file, poses):
    with open(output_file, 'w') as fd:
        for pose in poses:
            pose_line = ' '.join(map(str, pose.flatten())) + '\n'
            fd.write(pose_line)


def main(args):

    model = load_model(args.model_file, custom_objects={'weighted_mse': train.weighted_mse})

    image_paths, stamps, odom, num_outputs = train.load_filenames(args.input_dir, 'odom', args.stack_size, sequences=train.TEST_SEQUENCES)

    for sequence, (image_paths_, stamps_, odom_) in zip(train.TEST_SEQUENCES, zip(image_paths, stamps, odom)):

        print('Sequence: {}'.format(sequence))

        image_paths, stamps, odom = train.stack_data([image_paths_], [stamps_], [odom_], args.stack_size, test_phase=True)
        image_stacks = train.load_image_stacks(image_paths)

        predictions = model.predict(image_stacks)
        predictions *= train.ODOM_SCALES

        poses = calc_poses(predictions, stamps_, args.stack_size)

        output_file = os.path.join(args.output_dir, '{}.txt'.format(sequence))
        write_poses(output_file, poses)

        # vels = filename_loaders.poses_to_velocities(stamps_, poses, args.stack_size)
        # plot.plot_trajectory_2d(predictions, vels, stamps, args.stack_size)
        # plt.show()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('model_file', help='Model file')
    parser.add_argument('stack_size', type=int, help='Stack size')
    parser.add_argument('input_dir', help='Base directory')
    parser.add_argument('output_dir', help='Results directory')
    args = parser.parse_args()
    return args

if __name__ == '__main__':

    args = parse_args()
    main(args)
