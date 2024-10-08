import os

import megengine as mge
import megengine.functional as F
import argparse
import numpy as np
import cv2

from nets import Model


def load_model(model_path):
    print("Loading model:", os.path.abspath(model_path))
    pretrained_dict = mge.load(model_path)
    model = Model(max_disp=256, mixed_precision=False, test_mode=True)

    model.load_state_dict(pretrained_dict["state_dict"], strict=True)

    model.eval()
    return model


def inference(left, right, model, n_iter=20):
    print("Model Forwarding...")
    imgL = left.transpose(2, 0, 1)
    imgR = right.transpose(2, 0, 1)
    imgL = np.ascontiguousarray(imgL[None, :, :, :])
    imgR = np.ascontiguousarray(imgR[None, :, :, :])

    imgL = mge.tensor(imgL).astype("float32")
    imgR = mge.tensor(imgR).astype("float32")

    imgL_dw2 = F.nn.interpolate(
        imgL,
        size=(imgL.shape[2] // 2, imgL.shape[3] // 2),
        mode="bilinear",
        align_corners=True,
    )
    imgR_dw2 = F.nn.interpolate(
        imgR,
        size=(imgL.shape[2] // 2, imgL.shape[3] // 2),
        mode="bilinear",
        align_corners=True,
    )
    pred_flow_dw2 = model(imgL_dw2, imgR_dw2, iters=n_iter, flow_init=None)

    pred_flow = model(imgL, imgR, iters=n_iter, flow_init=pred_flow_dw2)
    pred_disp = F.squeeze(pred_flow[:, 0, :, :]).numpy()

    return pred_disp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A demo to run CREStereo.")
    parser.add_argument(
        "--model_path",
        default="crestereo_eth3d.mge",
        help="The path of pre-trained MegEngine model.",
    )
    parser.add_argument(
        "--size",
        default="1024x1536",
        help="The image size for inference. Te default setting is 1024x1536. \
                        To evaluate on ETH3D Benchmark, use 768x1024 instead.",
    )
    parser.add_argument(
        "--output", default="disparity.avi", help="The path of output disparity."
    )

    parser.add_argument(
        "--video_path", default="disparity.png", help="The path of video."
    )
    
    args = parser.parse_args()

    assert os.path.exists(args.model_path), "The model path do not exist."
    assert os.path.exists(args.video_path), "The video path do not exist."

    cap = cv2.VideoCapture('args.video_path')
    model_func = load_model(args.model_path)
    print("Images resized:", args.size)
    eval_h, eval_w = [int(e) for e in args.size.split("x")]
    out = cv2.VideoWriter(args.output ,cv2.VideoWriter_fourcc('M','J','P','G'), 10, (eval_w*3,eval_h))

    while(cap.isOpened()):
        ret, frame = cap.read()
        if ret == True:
            left = frame(Rect(0, 0, frame.cols/2, frame.rows));
            right = frame(Rect(frame.cols/2, 0, frame.cols, frame.rows));

            assert left.shape == right.shape, "The input images have inconsistent shapes."

            in_h, in_w = left.shape[:2]

            left_img = cv2.resize(left, (eval_w, eval_h), interpolation=cv2.INTER_LINEAR)
            right_img = cv2.resize(right, (eval_w, eval_h), interpolation=cv2.INTER_LINEAR)

            pred = inference(left_img, right_img, model_func, n_iter=20)

            t = float(in_w) / float(eval_w)
            disp = cv2.resize(pred, (in_w, in_h), interpolation=cv2.INTER_LINEAR) * t

            disp_vis = (disp - disp.min()) / (disp.max() - disp.min()) * 255.0
            disp_vis = disp_vis.astype("uint8")
            disp_vis = cv2.applyColorMap(disp_vis, cv2.COLORMAP_INFERNO)
            img3 = cv2.hconcat([left_image, right_image])
            img3 = cv2.hconcat([img3, disp_vis])
            out.write(img3)
            
        else: 
            break
    cap.release()
    out.release()
