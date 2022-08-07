from MazeSolver import *

mazesolver = MazeSolver()
continue_flag = True

while continue_flag:
    # 1byte受信
    print("from_pico:", end="")
    from_pico = int(input(), 2)
    print("Receive a byte fron input:{:08b}".format(from_pico))

    continue_flag, to_pico = mazesolver.calc_to_pico(from_pico)
    # 1byte送信
    print("Send a byte to output:{:08b}".format(to_pico))
