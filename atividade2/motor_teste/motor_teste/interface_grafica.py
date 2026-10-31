#!/usr/bin/env python3
import queue
import threading
import tkinter as tk

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from motor_interfaces.action import TestMotor, TestAllMotors

NUM_MOTORES = 7


def lista_texto(lista):
    return ', '.join(str(m) for m in lista) or '-'


class NoInterface(Node):

    def __init__(self, fila):
        super().__init__('interface_teste_motores')
        self.fila = fila
        self.client_motor = ActionClient(self, TestMotor, 'test_motor')
        self.client_todos = ActionClient(self, TestAllMotors, 'test_all_motors')

    def enviar_motor(self, motor):
        if not self.client_motor.server_is_ready():
            self.fila.put(('ind', 'Servidor de controle indisponivel'))
            return
        goal = TestMotor.Goal()
        goal.motor = motor
        futuro = self.client_motor.send_goal_async(
            goal, feedback_callback=self.feedback_motor)
        futuro.add_done_callback(self.resposta_motor)

    def feedback_motor(self, fb_msg):
        motor = fb_msg.feedback.active_motor
        self.fila.put(('ind', f'Testando motor {motor}...'))

    def resposta_motor(self, futuro):
        goal_handle = futuro.result()
        if not goal_handle.accepted:
            self.fila.put(('ind', 'Teste recusado (ja tem teste rodando)'))
            return
        goal_handle.get_result_async().add_done_callback(self.resultado_motor)

    def resultado_motor(self, futuro):
        result = futuro.result().result
        if result.success:
            self.fila.put(('ind', 'Concluido: ' + result.message))
        else:
            self.fila.put(('ind', 'Falha: ' + result.message))

    def enviar_todos(self):
        if not self.client_todos.server_is_ready():
            self.fila.put(('all', 'Servidor de controle indisponivel'))
            return
        self.fila.put(('testados', '-'))
        futuro = self.client_todos.send_goal_async(
            TestAllMotors.Goal(), feedback_callback=self.feedback_todos)
        futuro.add_done_callback(self.resposta_todos)

    def feedback_todos(self, fb_msg):
        fb = fb_msg.feedback
        if len(fb.active_motors) == NUM_MOTORES:
            texto = 'Testando todos juntos...'
        elif len(fb.active_motors) == 1:
            texto = f'Testando motor {fb.active_motors[0]}...'
        else:
            texto = 'Finalizando...'
        self.fila.put(('all', texto))
        self.fila.put(('testados', lista_texto(fb.tested_motors)))

    def resposta_todos(self, futuro):
        goal_handle = futuro.result()
        if not goal_handle.accepted:
            self.fila.put(('all', 'Teste recusado (ja tem teste rodando)'))
            return
        goal_handle.get_result_async().add_done_callback(self.resultado_todos)

    def resultado_todos(self, futuro):
        result = futuro.result().result
        self.fila.put(('testados', lista_texto(result.tested_motors)))
        if result.success:
            self.fila.put(('all', 'Teste completo concluido com sucesso'))
        else:
            self.fila.put(('all', 'Falha: ' + result.message))


class App:
    def __init__(self, root, no, fila):
        self.root = root
        self.fila = fila
        root.title('Teste dos Motores')

        tk.Label(root, text='Teste individual').pack(pady=(10, 0))
        frame = tk.Frame(root)
        frame.pack(padx=10)
        for i in range(1, NUM_MOTORES + 1):
            tk.Button(frame, text=f'Motor {i}',
                      command=lambda m=i: no.enviar_motor(m)).pack(side='left')
        label_ind = tk.Label(root, text='Aguardando')
        label_ind.pack()

        tk.Label(root, text='Teste completo').pack(pady=(10, 0))
        tk.Button(root, text='Iniciar teste completo',
                  command=no.enviar_todos).pack()
        label_all = tk.Label(root, text='Aguardando')
        label_all.pack()
        label_testados = tk.Label(root, text='-')
        label_testados.pack(pady=(0, 10))

        self.labels = {'ind': label_ind, 'all': label_all,
                       'testados': label_testados}
        self.atualizar()

    def atualizar(self):
        while not self.fila.empty():
            chave, texto = self.fila.get()
            self.labels[chave].config(text=texto)
        self.root.after(100, self.atualizar)


def main():
    rclpy.init()
    fila = queue.Queue()
    no = NoInterface(fila)

    threading.Thread(target=rclpy.spin, args=(no,), daemon=True).start()

    root = tk.Tk()
    App(root, no, fila)
    root.mainloop()

    no.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == '__main__':
    main()
