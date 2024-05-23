import os
import time
import docker
import yaml
from croniter import croniter
from datetime import datetime, timedelta

CONFIG_DIR = '/app/config'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.yaml')
TEMPLATE_FILE = '/app/templates/config.template.yaml'

# 设置 Docker 守护进程的地址和 API 版本
os.environ['DOCKER_HOST'] = 'tcp://localhost:2375'
os.environ['DOCKER_API_VERSION'] = '1.41'

# 创建 Docker 客户端
client = docker.from_env()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        create_default_config()
    with open(CONFIG_FILE, 'r') as file:
        return yaml.safe_load(file)

def create_default_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(TEMPLATE_FILE, 'r') as template, open(CONFIG_FILE, 'w') as config:
        config.write(template.read())

def is_container_running(container_name):
    try:
        container = client.containers.get(container_name)
        return container.status == 'running'
    except docker.errors.NotFound:
        return False

def start_container(container_name):
    try:
        container = client.containers.get(container_name)
        if container.status != 'running':
            container.start()
            print(f'Started container {container_name}')
    except docker.errors.NotFound:
        print(f'Container {container_name} not found')

def evaluate_condition(condition):
    if '|' in condition:
        return any(is_container_running(name.strip()) for name in condition.split('|'))
    elif '&' in condition:
        return all(is_container_running(name.strip()) for name in condition.split('&'))
    else:
        return is_container_running(condition)

def should_start_by_schedule(schedule, last_checked, delay):
    now = datetime.now()
    if croniter(schedule, now - timedelta(minutes=1)).get_next(datetime) <= now:
        if (now - last_checked).total_seconds() >= delay:
            return True
    return False

def main():
    config = load_config()
    dependencies = config['dependencies']

    last_checked = {container: datetime.min for container in dependencies}

    while True:
        now = datetime.now()
        for container, settings in dependencies.items():
            depends_on = settings.get('depends_on', [])
            schedule = settings.get('schedule', None)
            delay = settings.get('delay', 0)

            if is_container_running(container):
                continue  # 如果主容器已经运行，则跳过

            # 检查依赖条件
            if any(evaluate_condition(condition) for condition in depends_on):
                start_container(container)
                continue

            # 检查定时任务和延迟启动
            if schedule and should_start_by_schedule(schedule, last_checked[container], delay):
                start_container(container)
                last_checked[container] = now
                continue

            if delay > 0 and (now - last_checked[container]).total_seconds() >= delay:
                start_container(container)
                last_checked[container] = now
                continue

        time.sleep(5)  # 每5秒检查一次

if __name__ == "__main__":
    main()
