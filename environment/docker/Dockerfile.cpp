FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Install C++ toolchain, Python (for SciUnit), and basic tools
RUN apt-get update && apt-get install -y     build-essential cmake g++ git pkg-config     python3 python3-pip     && rm -rf /var/lib/apt/lists/*

# Copy SciUnit with pre-built binaries
COPY sciunit /opt/sciunit

# Skip cmake build step (binaries already pre-built in libexec/)
RUN cd /opt/sciunit &&     sed -i "s/cmdclass={'build_py': BuildCommand},//" setup.py &&     sed -i "s/data_files=.*//" setup.py &&     sed -i "s/setup_requires=.*//" setup.py &&     pip3 install .

# Verify
RUN sciunit --version && g++ --version | head -1 && cmake --version | head -1

WORKDIR /workspace
