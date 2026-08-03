FROM utiasasrl/vtr3:latest

RUN curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
RUN apt-get update
RUN apt-get install -y gz-harmonic ros-humble-ros-gzharmonic
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglvnd0 \
    libgl1 \
    libglx0 \
    libegl1 \
    mesa-utils && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p /usr/share/glvnd/egl_vendor.d && \
    echo '{\n\
    "file_format_version" : "1.0.0",\n\
    "ICD" : {\n\
        "library_path" : "libEGL_nvidia.so.0"\n\
    }\n\
}' > /usr/share/glvnd/egl_vendor.d/10_nvidia.json
ENV __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json