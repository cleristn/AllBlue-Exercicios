from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    controle = Node(
        package='motor_teste',
        executable='controle_motores',
        output='screen',
    )

    interface = Node(
        package='motor_teste',
        executable='interface_grafica',
        output='screen',
    )

    return LaunchDescription([controle, interface])
