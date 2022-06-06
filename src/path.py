import os

class PathNode():
    def __init__(self, x, y, z, pitch, roll, yaw) -> None:
        self.x, self.y, self.z, self.pitch, self.roll, self.yaw = \
            x, y, z, pitch, roll, yaw
        pass


class Trajectory():
    def __init__(self) -> None:
        self.path = []
        pass

    def __init__(self, log_path) -> None:
        self.path = []
        self.load_smith18_path(log_path)
        pass

    def load_smith18_path(self, log_path):
        f = open(log_path, 'r')
        lines = f.readlines()
        self.path = []
        for i, line in enumerate(lines):
            imagename, x, y, z, pitch, roll, yaw = line.split(',')
            # as the same format used in C++ program
            x, y, z, pitch, roll, yaw = - \
                float(x)/100, float(y)/100, float(z)/100, - \
                float(pitch), float(roll), 90-float(yaw)
            node = PathNode(x, y, z, pitch, roll, yaw)
            self.path.append(node)

    def len(self):
        return len(self.path)

    def is_empty(self):
        return self.len() == 0
