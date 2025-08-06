# vision_recheck.py – Optional visual confirmation before spray
import cv2

from ai_inference import BloomClassifier
from logger import setup_logger

def confirm_bloom(camera_index=0, min_frames=5, model_path="bloom_model.pt", confidence_threshold=0.7):
    logger = setup_logger("vision_recheck")
    cap = cv2.VideoCapture(camera_index)
    classifier = BloomClassifier(model_path)
    confirmed = False
    best_conf = 0.0
    frames = 0
    while frames < min_frames:
        ret, frame = cap.read()
        if not ret:
            logger.error("Camera read failed.")
            break
        labels, results = classifier.infer(frame)
        logger.info(f"Frame {frames}: labels={labels}")
        if 'female_bloom' in labels:
            df = results.pandas().xyxy[0]
            for _, row in df.iterrows():
                if row['name'] == 'female_bloom':
                    conf = row['confidence'] if 'confidence' in row else row.get('conf', 0.0)
                    best_conf = max(best_conf, conf)
                    if conf >= confidence_threshold:
                        confirmed = True
                        logger.info("Female bloom confirmed with confidence {:.2f}%".format(conf * 100))
                        break
        if confirmed:
            break
        frames += 1
    cap.release()
    logger.info(f"Bloom confirmation result: {confirmed}, best confidence: {best_conf:.2f}%")
    return confirmed, best_conf
