#!/usr/bin/env python3
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Int32MultiArray

from motor_interfaces.action import TestMotor, TestAllMotors

NUM_MOTORES = 7
PWM_NEUTRO = 1500
DURACAO = 2.0
PERIODO = 0.1


def forca_para_pwm(forca):
    return int(PWM_NEUTRO + forca * 50)


PWM_TESTE = forca_para_pwm(5.0)   # 1750


class ControleMotores(Node):
    def __init__(self):
        super().__init__('controle_motores')
        self.pub = self.create_publisher(Int32MultiArray, '/motors', 10)

        self.ocupado = False
        self.lock = threading.Lock()

        grupo = ReentrantCallbackGroup()

        self.server_motor = ActionServer(
            self, TestMotor, 'test_motor',
            execute_callback = self.executar_motor,
            goal_callback = self.goal_motor,
            cancel_callback = self.cancelar,
            callback_group = grupo)

        self.server_todos = ActionServer(
            self, TestAllMotors, 'test_all_motors',
            execute_callback = self.executar_todos,
            goal_callback = self.goal_todos,
            cancel_callback = self.cancelar,
            callback_group = grupo)

        self.parar()
        self.get_logger().info('Controle pronto')

    def publicar(self, lista):
        msg = Int32MultiArray()
        msg.data = lista
        self.pub.publish(msg)

    def parar(self):
        self.publicar([PWM_NEUTRO] * NUM_MOTORES)

    def montar_pwm(self, ativos):
        lista = [PWM_NEUTRO] * NUM_MOTORES
        for m in ativos:
            lista[m - 1] = PWM_TESTE
        return lista

    def manter_pwm(self, goal_handle, lista):
        fim = time.monotonic() + DURACAO
        while time.monotonic() < fim:
            if goal_handle.is_cancel_requested:
                return False
            self.publicar(lista)
            time.sleep(PERIODO)
        return True

    def reservar(self):
        with self.lock:
            if self.ocupado:
                return False
            self.ocupado = True
            return True

    def goal_motor(self, goal):
        if not 1 <= goal.motor <= NUM_MOTORES:
            return GoalResponse.REJECT
        if not self.reservar():
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def goal_todos(self, goal):
        if not self.reservar():
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancelar(self, goal_handle):
        return CancelResponse.ACCEPT

    def executar_motor(self, goal_handle):
        motor = goal_handle.request.motor
        result = TestMotor.Result()
        try:
            feedback = TestMotor.Feedback()
            feedback.active_motor = motor
            goal_handle.publish_feedback(feedback)

            if self.manter_pwm(goal_handle, self.montar_pwm([motor])):
                goal_handle.succeed()
                result.success = True
                result.message = f'Motor {motor} testado'
            else:
                goal_handle.canceled()
                result.success = False
                result.message = 'Cancelado'
        except Exception as e:
            goal_handle.abort()
            result.success = False
            result.message = str(e)
        finally:
            self.parar()
            self.ocupado = False
        return result

    def executar_todos(self, goal_handle):
        result = TestAllMotors.Result()
        feedback = TestAllMotors.Feedback()
        testados = []

        todos = list(range(1, NUM_MOTORES + 1))
        fases = [[m] for m in todos] + [todos]

        try:
            cancelado = False
            for i, ativos in enumerate(fases):
                feedback.active_motors = ativos
                feedback.tested_motors = testados
                feedback.progress = i / len(fases) * 100
                goal_handle.publish_feedback(feedback)

                if not self.manter_pwm(goal_handle, self.montar_pwm(ativos)):
                    cancelado = True
                    break
                if len(ativos) == 1:
                    testados.append(ativos[0])

            if cancelado:
                goal_handle.canceled()
                result.success = False
                result.message = 'Cancelado'
            else:
                feedback.active_motors = []
                feedback.tested_motors = testados
                feedback.progress = 100.0
                goal_handle.publish_feedback(feedback)
                goal_handle.succeed()
                result.success = True
                result.message = 'Teste completo concluido'
        except Exception as e:
            goal_handle.abort()
            result.success = False
            result.message = str(e)
        finally:
            self.parar()
            self.ocupado = False

        result.tested_motors = testados
        return result


def main():
    rclpy.init()
    no = ControleMotores()
    executor = MultiThreadedExecutor()
    executor.add_node(no)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            no.parar()
            no.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
