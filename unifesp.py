import cv2
import socket
import time

from mediapipe.python.solutions.hands import Hands, HandLandmark


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

        result = self.hands.process(image)

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


class TelloUDP:
    IP = "192.168.10.1"
    COMMAND_PORT = 8889

    def __init__(self):
        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        self.address = (
            self.IP,
            self.COMMAND_PORT
        )

    def send_command(self, command: str):
        print(f">>> {command}")

        self.socket.sendto(
            command.encode("utf-8"),
            self.address
        )

        return None

        try:
            self.socket.settimeout(5)

            response, _ = self.socket.recvfrom(1024)

            response = response.decode("utf-8")

            print(f"<<< {response}")

            return response

        except socket.timeout:
            print("<<< timeout")
            return None

        finally:
            self.socket.settimeout(None)

    def command(self):
        return self.send_command("command")

    def streamon(self):
        return self.send_command("streamon")

    def streamoff(self):
        return self.send_command("streamoff")

    def takeoff(self):
        return self.send_command("takeoff")

    def land(self):
        return self.send_command("land")

    def emergency(self):
        return self.send_command("emergency")

    def rc(self, left_right, forward_backward, up_down, yaw):
        command = (
            f"rc "
            f"{left_right} "
            f"{forward_backward} "
            f"{up_down} "
            f"{yaw}"
        )

        return self.send_command(command)

    def close(self):
        self.socket.close()


if __name__ == "__main__":

    detector = FingerDetector()

    tello = TelloUDP()

    # -------------------------
    # CONECTA AO TELLO
    # -------------------------

    print("Conectando ao Tello...")

    if tello.command() != "ok":
        raise RuntimeError("Não foi possível entrar no command mode")

    print("Tello conectado!")

    # -------------------------
    # INICIA VÍDEO
    # -------------------------

    tello.streamon()

    time.sleep(2)

    # Tello envia vídeo para UDP 11111
    video = cv2.VideoCapture(
        "udp://0.0.0.0:11111",
        cv2.CAP_FFMPEG
    )

    if not video.isOpened():
        raise RuntimeError(
            "Não foi possível abrir o stream de vídeo UDP"
        )

    try:
        while True:
            ret, frame = video.read()

            if not ret or frame is None:
                print("Erro ao capturar imagem")
                tello.rc(0, 0, 0, 0)
                continue

            cv2.imshow("Teste detector", frame)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                tello.rc(0, 0, 0, 0)
                break

            result = detector.detect(frame)
            print(f"detection: {result}")

            match result:
                case [1, 1, 1, 1, 0, 0, 1, 1, 1, 1]:  # Takeoff
                    tello.rc(0, 0, 0, 0)
                    tello.takeoff()
                case [0, 0, 0, 0, 1, 1, 0, 0, 0, 0]:  # Land
                    tello.rc(0, 0, 0, 0)
                    tello.land()

                case [0, 0, 0, 1, 0, 0, 1, 0, 0, 0]:  # Up
                    tello.rc(0, 0, 20, 0)
                case [0, 0, 0, 1, 1, 1, 1, 0, 0, 0]:  # Down
                    tello.rc(0, 0, -20, 0)

                case [0, 0, 0, 1, 1, 1, 1, 0, 0, 0]:  # Forward
                    tello.rc(0, 20, 0, 0)
                case [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]:  # Backward
                    tello.rc(0, -20, 0, 0)

                case [0, 0, 0, 0, 1, 1, 1, 0, 0, 0]:  # Left
                    tello.rc(20,  0,  0,  0)
                case [0, 0, 0, 1, 1, 1, 0, 0, 0, 0]:  # Right
                    tello.rc(-20, 0, 0, 0)

                case [1, 0, 0, 1, 1, 1, 1, 0, 0, 1]:  # Flip
                    tello.rc(0, 0, 0, 0)
                    tello.send_command("flip b")

                case _:
                    tello.rc(0, 0, 0, 0)

    finally:
        print("Encerrando...")
        tello.rc(0, 0, 0, 0)
        tello.streamoff()
        video.release()
        tello.close()
        cv2.destroyAllWindows()
