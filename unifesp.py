import cv2
from mediapipe.python.solutions.hands import Hands, HandLandmark
from djitellopy import Tello  # pip install djitellopy


class FingerDetector:
    def __init__(self):
        self.hands = Hands()

    def detect(self, image) -> list[int]:
        """
        Detecta quais dedos estão levantados.

        Retorno:
            [polegar, indicador, médio, anelar, mínimo]

        Cada valor:
            1 -> levantado
            0 -> abaixado
        """

        # OpenCV usa BGR, MediaPipe espera RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        result = self.hands.process(rgb)

        if (
            not result.multi_hand_landmarks
            or len(result.multi_hand_landmarks) != 2
        ):
            return None

        hand_left = result.multi_hand_landmarks[0].landmark
        hand_right = result.multi_hand_landmarks[1].landmark

        if hand_left[HandLandmark.WRIST].x > hand_right[HandLandmark.WRIST].x:
            hand_left, hand_right = hand_right, hand_left

        index_up_left = hand_left[HandLandmark.INDEX_FINGER_TIP].y < hand_left[HandLandmark.INDEX_FINGER_PIP].y
        middle_up_left = hand_left[HandLandmark.MIDDLE_FINGER_TIP].y < hand_left[HandLandmark.MIDDLE_FINGER_PIP].y
        ring_up_left = hand_left[HandLandmark.RING_FINGER_TIP].y < hand_left[HandLandmark.RING_FINGER_PIP].y
        pinky_up_left = hand_left[HandLandmark.PINKY_TIP].y < hand_left[HandLandmark.PINKY_PIP].y
        thumb_up_left = hand_left[HandLandmark.THUMB_IP].x < hand_left[HandLandmark.THUMB_TIP].x

        index_up_right = hand_right[HandLandmark.INDEX_FINGER_TIP].y < hand_right[HandLandmark.INDEX_FINGER_PIP].y
        middle_up_right = hand_right[HandLandmark.MIDDLE_FINGER_TIP].y < hand_right[HandLandmark.MIDDLE_FINGER_PIP].y
        ring_up_right = hand_right[HandLandmark.RING_FINGER_TIP].y < hand_right[HandLandmark.RING_FINGER_PIP].y
        pinky_up_right = hand_right[HandLandmark.PINKY_TIP].y < hand_right[HandLandmark.PINKY_PIP].y
        thumb_up_right = hand_right[HandLandmark.THUMB_TIP].x < hand_right[HandLandmark.THUMB_IP].x

        return [
            int(pinky_up_left),
            int(ring_up_left),
            int(middle_up_left),
            int(index_up_left),
            int(thumb_up_left),

            int(thumb_up_right),
            int(index_up_right),
            int(middle_up_right),
            int(ring_up_right),
            int(pinky_up_right),
        ]


if __name__ == '__main__':
    detector = FingerDetector()

    tello = Tello()
    tello.connect()
    tello.streamon()

    frame_read = tello.get_frame_read()

    while True:
        frame = frame_read.frame

        if not frame:
            print("Erro ao capturar imagem")
            tello.send_rc_control(0, 0, 0, 0)
            continue

        cv2.imshow('Teste detector', frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC para sair
            tello.send_rc_control(0, 0, 0, 0)
            cv2.destroyAllWindows()
            break

        result = detector.detect(frame)
        print(f'detection: {result}')

        match result:
            case [1, 1, 1, 1, 0, 0, 1, 1, 1, 1]:
                tello.send_rc_control(0, 0, 0, 0)
                tello.takeoff()
            case [0, 0, 0, 0, 1, 1, 0, 0, 0, 0]:
                tello.send_rc_control(0, 0, 0, 0)
                tello.land()

            case [0, 0, 0, 1, 0, 0, 1, 0, 0, 0]:
                tello.send_rc_control(0, 0, 20, 0)  # up
            case [0, 0, 0, 1, 1, 1, 1, 0, 0, 0]:
                tello.send_rc_control(0, 0, -20, 0)  # down

            case [0, 0, 0, 1, 1, 1, 1, 0, 0, 0]:
                tello.send_rc_control(0, 20, 0, 0)  # forward
            case [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]:
                tello.send_rc_control(0, -20, 0, 0)  # backward

            case [0, 0, 0, 0, 1, 1, 1, 0, 0, 0]:
                tello.send_rc_control(20, 0, 0, 0)  # left
            case [0, 0, 0, 1, 1, 1, 0, 0, 0, 0]:
                tello.send_rc_control(-20, 0, 0, 0)  # right

            case [1, 0, 0, 1, 1, 1, 1, 0, 0, 1]:
                tello.send_rc_control(0, 0, 0, 0)
                tello.flip_back()

            case _:
                tello.send_rc_control(0, 0, 0, 0)
