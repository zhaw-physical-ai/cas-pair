cmake_minimum_required(VERSION 3.8)
project(so101_description)

find_package(ament_cmake REQUIRED)

# $(find so101_description) and package://so101_description both look in share/
install(DIRECTORY urdf meshes launch
        DESTINATION share/${PROJECT_NAME})

ament_package()
