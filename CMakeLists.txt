cmake_minimum_required(VERSION 3.8)
project(ur12e_hande_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

install(DIRECTORY launch urdf config
  DESTINATION share/${PROJECT_NAME}
)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  ur12e_hande_bringup/hande_gripper_node.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
