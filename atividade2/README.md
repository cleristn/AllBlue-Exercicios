# Teste dos motores

Pacote ROS 2 que testa os 7 motores do AUV. Tem um nó de controle e uma interface com botões.

- `motor_interfaces`: as actions `TestMotor` e `TestAllMotors`.
- `motor_teste`: o nó de controle, a interface (tkinter) e o launch.

Cada teste aciona o motor por 2 segundos, publicando o PWM em `/motors`. Depois todos voltam para 1500. Se já tem um teste rodando, o outro é recusado.

## Rodar

```
cd ~/ros2_ws
colcon build --packages-select motor_interfaces motor_teste
source install/setup.bash
ros2 launch motor_teste teste_motores.launch.py
```

Precisa do tkinter: `sudo apt install python3-tk`
