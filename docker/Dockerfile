FROM ubuntu:latest

ENV TZ=America/New_York
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    net-tools \
    iproute2 \
    zsh \
    git \
    build-essential \
    libicu-dev \
    vim \
    nano \
    tzdata \
    iputils-ping \
    iperf3 \
    wget \
    ca-certificates \
    locales \
    libssl-dev \
    python3-dev \
    python3-venv \
    python3-pip \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Set UTF-8 as default locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Set working directory
WORKDIR /root

# Install Oh My Zsh (unattended)
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Customize prompt with [DOCKER] in ~/.zshrc
RUN echo 'PROMPT="%F{red}[DOCKER]%f %F{blue}%n@%m%f:%~ %# "' >> /root/.zshrc

# Set up virtual environment and install aioquic
RUN python3 -m venv /root/aioquic_env && \
    /root/aioquic_env/bin/pip install --upgrade pip && \
    /root/aioquic_env/bin/pip install aioquic

# Clone the aioquic_cm repo
RUN git clone https://github.com/prateekdceit06/aioquic_cm.git /root/aioquic_cm

# Set zsh as the default shell
CMD ["zsh"]
