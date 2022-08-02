"""
Todo
    - 坂とかのコスト計算
    - ロガー機能
    - 再開機能
"""


import numpy as np


# 被災者の定数

VICTIM_NONE = 0b000
VICTIM_H = 0b001
VICTIM_S = 0b010
VICTIM_U = 0b011
VICTIM_RED = 0b100
VICTIM_YELLOW = 0b101
VICTIM_GREEN = 0b110
VICTIM_HEATED = 0b111
MASK_VICTIM = 0b111

# Picoに送るときシフトする量
SHIFT_VICTIM_R = 3
SHIFT_VICTIM_L = 0

# 動作の定数
MOVE_FORWARD = 0b00000000
MOVE_RIGHT = 0b01000000
MOVE_LEFT = 0b10000000
MOVE_BACK = 0b11000000

# bitsの桁に対応する情報
BUMP_SLOPE = 7
BLACK = 6
SILVER = 5
HEAT_R = 4
HEAT_L = 3
WALL_R = 2
WALL_F = 1
WALL_L = 0

# 視覚的被災者の配列
victim = [VICTIM_NONE, VICTIM_NONE, VICTIM_NONE, VICTIM_NONE]
# 視覚的被災者の定数(victimのインデックス)
CHARACTER_R = 0
COLOR_R = 1
CHARACTER_L = 2
COLOR_L = 3

# 壁の状態
WALL_UNKNOWN = 0b00000
WALL_NONE = 0b01000
WALL_EXIST = 0b10000
WALL_VIRTUAL = 0b11000
MASK_WALL = 0b11000
MASK_WALL_EXIST = 0b10000

# 被災者と壁の組み合わせ
UNKNOWN = WALL_UNKNOWN & VICTIM_NONE

# タイルの状態
TILE_UNKNOWN = UNKNOWN
TILE_UNEXPLORED = 1
TILE_NONE = 2
TILE_SILVER = 3
TILE_BLACK = 4
TILE_BUMP_SLOPE = 5

# 配列の中で使わない場所
UNUSED = 0b0000_0000

# コストの定数
COST_MOVE = 1
COST_TURN = 1
COST_BUMP = 10000

# 開始時をNORTHとした絶対的な向き
NORTH = 0
WEST = 1
SOUTH = 2
EAST = 3

# ロボットからみた向き
FRONT = 0
LEFT = 1
BACK = 2
RIGHT = 3

# 操作量(Manipulated Value) 順にNORTH, WEST, SOUTH, EAST
MV = ((-1, 0), (0, -1), (1, 0), (0, 1))

# x,y軸の定数(インデックス)
x, y = (1, 0)


class MazeSolver():
    # 迷路のマップ
    map_maze = np.array([
        [UNUSED, UNKNOWN, UNUSED],
        [UNKNOWN, UNKNOWN, UNKNOWN],
        [UNUSED, UNKNOWN, UNUSED]
    ])
    # 通った回数のマップ
    map_count = np.array([0])
    # マップのサイズ(y,x)
    map_size = [1, 1]
    # ロボットの位置(y,x)
    position = [1, 1]
    # 開始位置
    start_position = [1, 1]

    # 現在のロボットの向き
    direction = NORTH

    # 未探索タイルのリスト
    unknown_tiles = []
    # 経路
    path = []
    # 経路をたどっているか
    is_routing = False
    # 探索の初回か
    is_first = True

    def __init__(self):
        # 最初に各方向に1つずつマップを拡張
        for i in range(4):
            self.extend_map(i)

    def set_map(self, status: int, direction_from_robot: int | None = None, is_tile: bool = False):
        """マップにデータをsetする関数

        Args:
            status (int): マップにsetするデータ
            direction_from_robot (int | None, optional): setする壁の向き(タイルの場合設定しない(None)). Defaults to None.
            is_tile: タイルをsetするか デフォルトはfalse(壁をsetする)
        """
        if direction_from_robot == None:
            self.map_maze[self.position[y]][self.position[x]] = status
        elif is_tile:
            self.map_maze[self.position[y]+(MV[(self.direction+direction_from_robot) % 4][y])*2
                          ][self.position[x] + (MV[(self.direction+direction_from_robot) % 4][x])*2] = status
        else:
            self.map_maze[self.position[y]+MV[(self.direction+direction_from_robot) % 4][y]
                          ][self.position[x] + MV[(self.direction+direction_from_robot) % 4][x]] |= status

    def get_map(self, position: tuple[int, int], direction: int, direction_from_robot: int | None = None, is_tile: bool = False) -> int:
        """マップの情報をgetする関数

        Args:
            position: getするposition
            direction: 機体の絶対的な向き
            direction_from_robot (int | None, optional): getする壁の向き(タイルの場合設定しない(None)). Defaults to None.
            is_tile: タイルをgetするか デフォルトはfalse(壁をgetする)

        Returns:
            int: getした値
        """
        if direction_from_robot == None:
            return self.map_maze[position[y]][position[x]]
        elif is_tile:
            return self.map_maze[position[y]+(MV[(direction+direction_from_robot) % 4][y])*2
                                 ][position[x] + (MV[(direction+direction_from_robot) % 4][x])*2]
        else:
            return self.map_maze[position[y]+MV[(direction+direction_from_robot) % 4][y]
                                 ][position[x] + MV[(direction+direction_from_robot) % 4][x]]

    def change_position(self, move: int):
        """moveの値に従ってpositionとdirectionを変える関数
        """
        if move == MOVE_FORWARD:
            self.position[x] += MV[(self.direction+FRONT) % 4][x]*2
            self.position[y] += MV[(self.direction+FRONT) % 4][y]*2
        elif move == MOVE_RIGHT:
            self.direction -= 1
            self.change_position(MOVE_FORWARD)
        elif move == MOVE_LEFT:
            self.direction += 1
            self.change_position(MOVE_FORWARD)
        elif move == MOVE_BACK:
            self.direction += 2
            self.change_position(MOVE_FORWARD)
        if self.position[x] <= 1:
            self.extend_map(WEST)
        elif self.position[x] >= (self.map_size[x]-1)*2:
            self.extend_map(EAST)
        elif self.position[y] <= 1:
            self.extend_map(NORTH)
        elif self.position[y] >= (self.map_size[y]-1)*2:
            self.extend_map(SOUTH)

    def get_position(self, position: tuple[int, int], direction: int, direction_from_robot: int) -> list[int, int]:
        """任意のposition,direction,direction_robotからpositionを計算する関数

        Args:
            position (_type_): position
            direction (_type_): 機体の向き
            direction_from_robot (_type_): 機体からみた向き

        Returns:
            list[int,int]: 計算したposition
        """
        return [position[y]+(MV[(direction+direction_from_robot) % 4][y])*2,
                position[x]+(MV[(direction+direction_from_robot) % 4][x])*2]

    def calc_path(self, start_position: tuple[int, int], goal_position: tuple[int, int]) -> list:
        position = goal_position
        cost_map = np.full(self.map_size, np.inf)
        direction = NORTH
        paths = []
        continue_flag = True
        answer_paths = []
        # 初回だけ例外処理(direction)
        if position[y] > 1:
            # 北に壁がないかつ北のタイルが探索済みか
            if (self.get_map(position, direction, FRONT) & MASK_WALL_EXIST != WALL_EXIST
                    and self.get_map(position, direction, FRONT, True) != TILE_UNKNOWN
                    and self.get_map(position, direction, FRONT, True) != TILE_UNEXPLORED):
                position_temp = self.get_position(position, direction, FRONT)
                # スタートに到達した
                if position_temp == start_position:
                    continue_flag = False
                    answer_paths.append([[position], (1, NORTH)])
                else:
                    cost_map[position_temp[y]//2][position_temp[x]//2] = 1
                    paths.append([[position_temp, goal_position], (1, NORTH)])
        if position[x] < self.map_size[x]*2-1:
            # 東に壁がないかつ東のタイルが探索済みか
            if (self.get_map(position, direction, RIGHT) & MASK_WALL_EXIST != WALL_EXIST
                    and self.get_map(position, direction, RIGHT, True) != TILE_UNKNOWN
                    and self.get_map(position, direction, RIGHT, True) != TILE_UNEXPLORED):
                position_temp = self.get_position(position, direction, RIGHT)
                # スタートに到達した
                if position_temp == start_position:
                    continue_flag = False
                    answer_paths.append([[position], (1, EAST)])
                else:
                    cost_map[position_temp[y]//2][position_temp[x]//2] = 1
                    paths.append([[position_temp, goal_position], (1, EAST)])
        if position[x] > 1:
            # 西に壁がないかつ西のタイルが探索済みか
            if (self.get_map(position, direction, LEFT) & MASK_WALL_EXIST != WALL_EXIST
                    and self.get_map(position, direction, LEFT, True) != TILE_UNKNOWN
                    and self.get_map(position, direction, LEFT, True) != TILE_UNEXPLORED):
                position_temp = self.get_position(position, direction, LEFT)
                # スタートに到達した
                if position_temp == start_position:
                    continue_flag = False
                    answer_paths.append([[position], (1, WEST)])
                else:
                    cost_map[position_temp[y]//2][position_temp[x]//2] = 1
                    paths.append([[position_temp, goal_position], (1, WEST)])
        if position[y] < self.map_size[y]*2-1:
            # 南に壁がないかつ南のタイルが探索済みか
            if (self.get_map(position, direction, BACK) & MASK_WALL_EXIST != WALL_EXIST
                    and self.get_map(position, direction, BACK, True) != TILE_UNKNOWN
                    and self.get_map(position, direction, BACK, True) != TILE_UNEXPLORED):
                position_temp = self.get_position(position, direction, BACK)
                # スタートに到達した
                if position_temp == start_position:
                    continue_flag = False
                    answer_paths.append(paths[[position], (1, SOUTH)])
                else:
                    cost_map[position_temp[y]//2][position_temp[x]//2] = 1
                    paths.append([[position_temp, goal_position], (1, SOUTH)])
        # 最短経路を求めていく
        while continue_flag:
            paths.sort(key=lambda x: x[1][0])
            cost = paths[0][1][0]
            min_paths = [i for i in paths if i[1][0] == cost]
            paths = [i for i in paths if i[1][0] > cost]
            for path in min_paths:
                position = path[0][0]
                direction = path[1][1]
                # 前に壁がないかつ前のタイルが探索済みか
                if (self.get_map(position, direction, FRONT) & MASK_WALL_EXIST != WALL_EXIST
                        and self.get_map(position, direction, FRONT, True) != TILE_UNKNOWN
                        and self.get_map(position, direction, FRONT, True) != TILE_UNEXPLORED):
                    position_temp = self.get_position(position, direction, FRONT)
                    # スタートに到達した
                    if position_temp == start_position:
                        continue_flag = False
                        answer_paths.append(path)
                    elif self.get_map(position, direction, FRONT) == TILE_BUMP_SLOPE:
                        # 今のコスト+COST_BUMPが移動先のタイルのコストより小さい
                        if cost+COST_BUMP < cost_map[position_temp[y]//2][position_temp[x]//2]:
                            cost_map[position_temp[y]//2][position_temp[x]//2] = cost+COST_BUMP
                            paths.append([[position_temp]+path[0], (cost+COST_BUMP, direction)])
                    else:
                        # 今のコスト+COST_MOVEが移動先のタイルのコストより小さい
                        if cost+COST_MOVE < cost_map[position_temp[y]//2][position_temp[x]//2]:
                            cost_map[position_temp[y]//2][position_temp[x]//2] = cost+COST_MOVE
                            paths.append([[position_temp]+path[0], (cost+COST_MOVE, direction)])
                # 右に壁がないかつ右のタイルが探索済みか
                if (self.get_map(position, direction, RIGHT) & MASK_WALL_EXIST != WALL_EXIST
                        and self.get_map(position, direction, RIGHT, True) != TILE_UNKNOWN
                        and self.get_map(position, direction, RIGHT, True) != TILE_UNEXPLORED):
                    position_temp = self.get_position(position, direction, RIGHT)
                    # スタートに到達した
                    if position_temp == start_position:
                        continue_flag = False
                        answer_paths.append(path)
                    elif self.get_map(position, direction, RIGHT) == TILE_BUMP_SLOPE:
                        # 今のコスト+COST_BUMPが移動先のタイルのコストより小さい
                        if cost+COST_BUMP < cost_map[position_temp[y]//2][position_temp[x]//2]:
                            cost_map[position_temp[y]//2][position_temp[x]//2] = cost+COST_BUMP
                            paths.append([[position_temp]+path[0], (cost+COST_BUMP, direction)])
                    else:
                        # 今のコスト+COST_MOVE+COST_TURNが移動先のタイルのコストより小さい
                        if cost+COST_MOVE+COST_TURN < cost_map[position_temp[y]//2][position_temp[x]//2]:
                            cost_map[position_temp[y]//2][position_temp[x]//2] = cost+COST_MOVE+COST_TURN
                            paths.append([[position_temp]+path[0], (cost+COST_MOVE+COST_TURN, direction)])
                # 左に壁がないかつ左のタイルが探索済みか
                if (self.get_map(position, direction, LEFT) & MASK_WALL_EXIST != WALL_EXIST
                        and self.get_map(position, direction, LEFT, True) != TILE_UNKNOWN
                        and self.get_map(position, direction, LEFT, True) != TILE_UNEXPLORED):
                    position_temp = self.get_position(position, direction, LEFT)
                    # スタートに到達した
                    if position_temp == start_position:
                        continue_flag = False
                        answer_paths.append(path)
                    elif self.get_map(position, direction, LEFT) == TILE_BUMP_SLOPE:
                        # 今のコスト+COST_BUMPが移動先のタイルのコストより小さい
                        if cost+COST_BUMP < cost_map[position_temp[y]//2][position_temp[x]//2]:
                            cost_map[position_temp[y]//2][position_temp[x]//2] = cost+COST_BUMP
                            paths.append([[position_temp]+path[0], (cost+COST_BUMP, direction)])
                    else:
                        # 今のコスト+COST_MOVE+COST_TURNが移動先のタイルのコストより小さい
                        if cost+COST_MOVE+COST_TURN < cost_map[position_temp[y]//2][position_temp[x]//2]:
                            cost_map[position_temp[y]//2][position_temp[x]//2] = cost+COST_MOVE+COST_TURN
                            paths.append([[position_temp]+path[0], (cost+COST_MOVE+COST_TURN, direction)])
        min_cost = float('inf')
        answer_path = []
        for path in answer_paths:
            if path[1][0] < min_cost:
                min_cost = path[1][0]
                answer_path = path
        return answer_path[0]

    def extend_map(self, direction: int):
        if direction == NORTH:
            temp = [[UNKNOWN for i in range(self.map_size[x]*2+1)]for j in range(2)]
            self.map_maze = np.vstack((temp, self.map_maze))
            temp = [0 for i in range(self.map_size[x])]
            self.map_count = np.vstack((temp, self.map_count))
            self.map_size[y] += 1
            self.position[y] += 2
            self.start_position[y] += 2
            for tile in self.unknown_tiles:
                tile[y] += 2
        elif direction == SOUTH:
            temp = [[UNKNOWN for i in range(self.map_size[x]*2+1)]for j in range(2)]
            self.map_maze = np.vstack((self.map_maze, temp))
            temp = [0 for i in range(self.map_size[x])]
            self.map_count = np.vstack((self.map_count, temp))
            self.map_size[y] += 1
        elif direction == WEST:
            temp = [[UNKNOWN, UNKNOWN]for i in range(self.map_size[y]*2+1)]
            self.map_maze = np.hstack((temp, self.map_maze))
            temp = [[0] for i in range(self.map_size[y])]
            self.map_count = np.hstack((temp, self.map_count))
            self.map_size[x] += 1
            self.position[x] += 2
            self.start_position[x] += 2
            for tile in self.unknown_tiles:
                tile[x] += 2
        elif direction == EAST:
            temp = [[UNKNOWN, UNKNOWN]for i in range(self.map_size[y]*2+1)]
            self.map_maze = np.hstack((self.map_maze, temp))
            temp = [[0] for i in range(self.map_size[y])]
            self.map_count = np.hstack((self.map_count, temp))
            self.map_size[x] += 1

    def draw_map(self):
        print("   ", end="")
        for i in range(self.map_size[x]*2+1):
            print("{:2d} ".format(i), end="")
        print()
        for i in range(self.map_size[y]*2+1):
            print("{:2d}".format(i), end=" ")
            for j in range(self.map_size[x]*2+1):
                if self.map_maze[i][j] & MASK_WALL == WALL_EXIST:
                    if i % 2 == 0:
                        print("━━━", end="")
                    else:
                        print(" ┃ ", end="")
                elif self.map_maze[i][j] & MASK_WALL == WALL_VIRTUAL:
                    if i % 2 == 0:
                        print("───", end="")
                    else:
                        print(" │ ", end="")
                elif [i, j] == self.position:
                    if self.direction % 4 == NORTH:
                        print(" ↑ ", end="")
                    elif self.direction % 4 == WEST:
                        print(" ← ", end="")
                    elif self.direction % 4 == SOUTH:
                        print(" ↓ ", end="")
                    elif self.direction % 4 == EAST:
                        print(" → ", end="")
                else:
                    print("   ", end="")
            print("")

    def calc_move(self, from_pico: int) -> tuple[bool, int]:
        start_flag = True
        # ビットマスク
        bits = []
        for i in range(8):
            bits.append(True if 1 & from_pico >> i else False)

        # 7bit バンプ・坂道・階段通過
        if bits[BUMP_SLOPE]:
            print("Passed bump/stairs/slope")
            self.set_map(TILE_BUMP_SLOPE)
            self.set_map(WALL_EXIST, RIGHT)
            self.set_map(WALL_EXIST, LEFT)
            self.change_position(MOVE_FORWARD)

        # 6bit 黒タイル戻り
        if bits[BLACK]:
            print("Found black")
            self.set_map(TILE_BLACK)
            if self.position in self.unknown_tiles:
                self.unknown_tiles.remove(self.position)
            self.change_position(MOVE_BACK)
            self.direction += 2
            self.set_map(WALL_VIRTUAL, FRONT)

        if not (bits[BUMP_SLOPE] | bits[BLACK]):
            self.set_map(TILE_NONE)

        # 壁の情報出力
        print("Wall R:{}, F:{}, L:{}".format(bits[WALL_R], bits[WALL_F], bits[WALL_L]))

        if not bits[BLACK]:
            self.set_map(WALL_EXIST if bits[WALL_R] else WALL_NONE, RIGHT)
            self.set_map(WALL_EXIST if bits[WALL_F] else WALL_NONE, FRONT)
            self.set_map(WALL_EXIST if bits[WALL_L] else WALL_NONE, LEFT)

        """ if bits[WALL_R]:
            print("Character victim on right:", end="")
            victim[CHARACTER_R] = int(input())
            print("Color victim on right:", end="")
            victim[COLOR_R] = int(input())
        if bits[WALL_L]:
            print("Character victim on left:", end="")
            victim[CHARACTER_L] = int(input())
            print("Color victim on left:", end="")
            victim[COLOR_L] = int(input()) """

        to_pico = 0

        if bits[HEAT_R]:
            if(self.get_map(self.position, self.direction, RIGHT) & MASK_VICTIM == VICTIM_NONE):
                self.set_map(VICTIM_HEATED, RIGHT)
                to_pico |= VICTIM_HEATED << SHIFT_VICTIM_R
        elif victim[CHARACTER_R] != VICTIM_NONE:
            if(self.get_map(self.position, self.direction, RIGHT) & MASK_VICTIM == VICTIM_NONE):
                self.set_map(victim[CHARACTER_R], RIGHT)
                to_pico |= victim[CHARACTER_R] << SHIFT_VICTIM_R
        elif victim[COLOR_R] != VICTIM_NONE:
            self.set_map(victim[COLOR_R], RIGHT)
            if(self.get_map(self.position, self.direction, RIGHT) & MASK_VICTIM == VICTIM_NONE):
                self.set_map(victim[COLOR_R], RIGHT)
                to_pico |= victim[COLOR_R] << SHIFT_VICTIM_R

        if bits[HEAT_L]:
            if(self.get_map(self.position, self.direction, LEFT) & MASK_VICTIM == VICTIM_NONE):
                self.set_map(VICTIM_HEATED, LEFT)
                to_pico |= VICTIM_HEATED << SHIFT_VICTIM_L
        elif victim[CHARACTER_L] != VICTIM_NONE:
            if(self.get_map(self.position, self.direction, LEFT) & MASK_VICTIM == VICTIM_NONE):
                self.set_map(victim[CHARACTER_L], LEFT)
                to_pico |= victim[CHARACTER_L] << SHIFT_VICTIM_L
        elif victim[COLOR_L] != VICTIM_NONE:
            if(self.get_map(self.position, self.direction, LEFT) & MASK_VICTIM == VICTIM_NONE):
                self.set_map(victim[COLOR_L], LEFT)
                to_pico |= victim[COLOR_L] << SHIFT_VICTIM_L

        move = 0

        # 今のタイルが未探索リストにあったなら削除する
        if self.position in self.unknown_tiles:
            self.unknown_tiles.remove(self.position)
        if not self.is_routing:
            if self.is_first:
                self.set_map(WALL_EXIST, BACK)
                self.is_first = False
            # 右に壁がないか
            if self.get_map(self.position, self.direction, RIGHT) & MASK_WALL_EXIST != WALL_EXIST:
                right_position = self.get_position(self.position, self.direction, RIGHT)
                # 右のタイルが未知か
                if self.get_map(self.position, self.direction, RIGHT, True) == TILE_UNKNOWN:
                    self.unknown_tiles.append(right_position)
                    self.set_map(TILE_UNEXPLORED, RIGHT, True)
            # 前に壁がないか
            if self.get_map(self.position, self.direction, FRONT) & MASK_WALL_EXIST != WALL_EXIST:
                front_position = self.get_position(self.position, self.direction, FRONT)
                # 前のタイルが未知か
                if self.get_map(self.position, self.direction, FRONT, True) == TILE_UNKNOWN:
                    self.unknown_tiles.append(front_position)
                    self.set_map(TILE_UNEXPLORED, FRONT, True)
            # 左に壁がないか
            if self.get_map(self.position, self.direction, LEFT) & MASK_WALL_EXIST != WALL_EXIST:
                left_position = self.get_position(self.position, self.direction, LEFT)
                # 左のタイルが未知か
                if self.get_map(self.position, self.direction, LEFT, True) == TILE_UNKNOWN:
                    self.unknown_tiles.append(left_position)
                    self.set_map(TILE_UNEXPLORED, LEFT, True)
            # 右に壁がないかつ右のタイルが既知かつ未探索か
            if self.get_map(self.position, self.direction, RIGHT) & MASK_WALL_EXIST != WALL_EXIST and self.get_map(self.position, self.direction, RIGHT, True) == TILE_UNEXPLORED:
                move = MOVE_RIGHT
            # 前に壁がないかつ前のタイルが既知かつ未探索か
            elif self.get_map(self.position, self.direction, FRONT) & MASK_WALL_EXIST != WALL_EXIST and self.get_map(self.position, self.direction, FRONT, True) == TILE_UNEXPLORED:
                move = MOVE_FORWARD
            # 左に壁がないかつ左のタイルが既知かつ未探索か
            elif self.get_map(self.position, self.direction, LEFT) & MASK_WALL_EXIST != WALL_EXIST and self.get_map(self.position, self.direction, LEFT, True) == TILE_UNEXPLORED:
                move = MOVE_LEFT
            # それ以外 = 行き止まり
            else:
                # 未探索タイルがなければスタートに戻る
                if len(self.unknown_tiles) == 0 and not self.is_first:
                    self.path = self.calc_path(self.position, self.start_position)
                    self.is_routing = True
                # unknown_tilesの末尾のタイルに移動
                else:
                    self.path = self.calc_path(self.position, self.unknown_tiles[-1])
                    self.is_routing = True

        if self.is_routing:
            print('routing')
            position_next = self.path.pop(0)
            if len(self.path) == 0:
                self.is_routing = False
                if len(self.unknown_tiles) == 0:
                    start_flag = False
            if self.get_position(self.position, self.direction, FRONT) == position_next:
                move = MOVE_FORWARD
            elif self.get_position(self.position, self.direction, RIGHT) == position_next:
                move = MOVE_RIGHT
            elif self.get_position(self.position, self.direction, LEFT) == position_next:
                move = MOVE_LEFT
            elif self.get_position(self.position, self.direction, BACK) == position_next:
                move = MOVE_BACK
        if move == MOVE_FORWARD:
            print('Move forward')
        elif move == MOVE_RIGHT:
            print('Move right')
        elif move == MOVE_LEFT:
            print('Move left')
        elif move == MOVE_BACK:
            print('Move back')
        print('Unknown tiles:', self.unknown_tiles)
        self.draw_map()
        to_pico |= move
        self.change_position(move)
        return start_flag, to_pico
