# Ansible Integration Guide

This document describes how to use `db-name-to-idx-mapper` in Ansible playbooks for automatic Redis/Valkey database configuration in container deployments.

## Problem Overview

When deploying applications in containers that use Redis with mapped database names:
1. Each application registers its databases via `mapper.ensure_mapping()` calls
2. Redis needs a `databases = N` parameter with a sufficiently large number
3. If Redis doesn't have enough databases, applications fail with "invalid DB index" errors

This guide solves this deployment challenge with Ansible automation.

## Prerequisites

- Applications use `db-name-to-idx-mapper` with `ensure_mapping()` calls in their configuration/startup code:
  - **Django**: `settings.py`
  - **FastAPI**: `config.py` or `main.py`
  - **Flask**: `config.py` or `app.py`
  - **Other frameworks**: any module registering the mappings. Ideally, the file would be doing just the mappings 
    (no mutations in setup phase) 
- Shared config volume between containers for `/etc/db-name-to-idx-mapper/config.json`
- Redis configuration via `REDIS_DATABASES` environment variable

## Ansible Variables

```yaml
# group_vars/all.yml or host_vars/
redis_databases: 16  # Redis default
mapper_config_path: "/etc/db-name-to-idx-mapper"
```

## Basic Deployment Workflow

```yaml
---
- name: Deploy applications with Redis auto-configuration
  hosts: app_servers
  become: yes
  
  tasks:
    - name: Create shared config directory
      file:
        path: "{{ mapper_config_path }}"
        state: directory
        owner: root
        group: root
        mode: '0755'

    - name: Deploy applications for mapping registration
      docker_container:
        name: "{{ item.name }}-discovery"
        image: "{{ item.image }}"
        command: "{{ item.discovery_command | default('python -c \"import settings\"') }}"  # Trigger ensure_mapping() calls
        volumes:
          - "{{ mapper_config_path }}:{{ mapper_config_path }}"
        auto_remove: yes
        detach: no  # Wait for completion
      loop: "{{ app_containers }}"
      tags: discovery

    - name: Read required number of Redis databases
      shell: |
        if [ -f {{ mapper_config_path }}/config.json ]; then
          python3 -c "
          import json
          with open('{{ mapper_config_path }}/config.json') as f:
            config = json.load(f)
          mappings = config.get('mappings', {})
          print(max(mappings.values()) if mappings else -1)
          "
        else
          echo -1
        fi
      register: required_max_idx
      tags: discovery

    - name: Update Redis databases variable
      set_fact:
        calculated_redis_databases: "{{ [redis_databases | int, (required_max_idx.stdout | int) + 10] | max }}"
      tags: discovery

    - name: Start Redis with appropriate number of databases
      docker_container:
        name: redis
        image: redis:7-alpine
        environment:
          REDIS_DATABASES: "{{ calculated_redis_databases }}"
        volumes:
          - redis_data:/data
        ports:
          - "6379:6379"
        restart_policy: unless-stopped
      tags: redis

    - name: Wait for Redis to start
      wait_for:
        host: localhost
        port: 6379
        timeout: 30
      tags: redis

    - name: Deploy production applications
      docker_container:
        name: "{{ item.name }}"
        image: "{{ item.image }}"
        volumes:
          - "{{ mapper_config_path }}:{{ mapper_config_path }}:ro"
        environment: "{{ item.environment | default({}) }}"
        restart_policy: unless-stopped
        networks:
          - name: app_network
      loop: "{{ app_containers }}"
      tags: apps

    - name: Display configuration
      debug:
        msg: 
          - "Redis configured with {{ calculated_redis_databases }} databases"
          - "Maximum mapping index: {{ required_max_idx.stdout }}"
          - "Config location: {{ mapper_config_path }}/config.json"
      tags: info
```

## Example Inventory Structure

```yaml
# group_vars/all.yml
app_containers:
  - name: web-app
    image: mycompany/web-app:latest
    discovery_command: "python -c 'import settings'"  # Django
    environment:
      DATABASE_URL: "postgresql://..."
      
  - name: fastapi-app
    image: mycompany/fastapi-app:latest  
    discovery_command: "python -c 'import config'"  # FastAPI
    environment:
      REDIS_URL: "redis://redis:6379"

  - name: flask-worker
    image: mycompany/flask-worker:latest
    discovery_command: "python -c 'from app import create_app; create_app()'"  # Flask
    environment:
      CELERY_BROKER: "redis://redis:6379/0"

# Applications use shared volume for config
mapper_config_path: "/etc/db-name-to-idx-mapper"
redis_databases: 20
```

## Docker Compose Integration

If using Docker Compose with Ansible:

```yaml
# templates/docker-compose.yml.j2
version: '3.8'

volumes:
  redis_data:
  db_mappings:

services:
  redis:
    image: redis:7-alpine
    environment:
      - REDIS_DATABASES={{ calculated_redis_databases | default(redis_databases) }}
    volumes:
      - redis_data:/data
    
  {% for app in app_containers %}
  {{ app.name }}:
    image: {{ app.image }}
    volumes:
      - db_mappings:{{ mapper_config_path }}
    depends_on:
      - redis
    environment:
      {% for key, value in app.environment.items() %}
      - {{ key }}={{ value }}
      {% endfor %}
  {% endfor %}
```

```yaml
# Ansible task
- name: Generate docker-compose.yml
  template:
    src: docker-compose.yml.j2
    dest: "{{ project_path }}/docker-compose.yml"
  notify: restart_containers
```

## Troubleshooting

### Debug Mappings

```yaml
- name: Display current mappings
  shell: |
    if [ -f {{ mapper_config_path }}/config.json ]; then
      python3 -c "
      import json
      with open('{{ mapper_config_path }}/config.json') as f:
        config = json.load(f)
      for name, idx in sorted(config.get('mappings', {}).items()):
        print(f'{name}: {idx}')
      "
    else
      echo 'Config file does not exist'
    fi
  register: current_mappings

- debug: var=current_mappings.stdout_lines
```

### Check Redis Configuration

```yaml
- name: Check Redis databases setting
  command: docker exec redis redis-cli CONFIG GET databases
  register: redis_config

- debug: var=redis_config.stdout
```

### Manually Add Mappings

```yaml
- name: Manually add mapping
  shell: |
    python3 -c "
    import json, os
    config_file = '{{ mapper_config_path }}/config.json'
    
    if os.path.exists(config_file):
      with open(config_file) as f:
        config = json.load(f)
    else:
      config = {'mappings': {}, 'utilities': {}}
    
    mappings = config['mappings']
    name = '{{ mapping_name }}'
    
    if name not in mappings:
      next_idx = max(mappings.values(), default=-1) + 1
      mappings[name] = next_idx
      print(f'Added {name} -> {next_idx}')
      
      with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, sort_keys=True)
    else:
      print(f'Mapping {name} already exists: {mappings[name]}')
    "
  vars:
    mapping_name: "myapp.newfeature"
```

## Best Practices

1. **Always add buffer** - `max_index + 10` instead of `max_index + 1`
2. **Use tags** for selective execution (`--tags discovery,redis`)
3. **Backup config** before changes using `backup: yes` in template modules
4. **Monitor deployment** with health checks for Redis connectivity
5. **Document mappings** in comments or README files

## Advanced Options

### Rolling Updates

```yaml
- name: Rolling update with preserved mappings
  include_tasks: rolling_update.yml
  vars:
    preserve_mappings: true
```

### Multiple Environments

```yaml
# group_vars/production.yml
mapper_config_path: "/etc/db-name-to-idx-mapper"
redis_databases: 50

# group_vars/staging.yml  
mapper_config_path: "/tmp/db-name-to-idx-mapper"
redis_databases: 20
```

### Backup and Restore

```yaml
- name: Backup mappings
  copy:
    src: "{{ mapper_config_path }}/config.json"
    dest: "{{ backup_path }}/db-mappings-{{ ansible_date_time.epoch }}.json"
    remote_src: yes
  tags: backup
```

For more information about basic library usage, see [README.md](README.md).
