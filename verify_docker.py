#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Docker 配置验证脚本"""

import os
import sys
import yaml

def test_docker_config():
    """验证 Docker 配置的正确性"""
    
    print("=" * 60)
    print("ArchiveBot Docker 配置验证")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # 1. 检查必需文件
    print("\n[1/7] 检查必需文件...")
    required_files = {
        'Dockerfile': '容器镜像构建文件',
        'docker-compose.yml': '容器编排配置',
        '.dockerignore': '构建排除文件',
        'main.py': 'Bot 主程序',
        'requirements.txt': 'Python 依赖',
        'config/config.template.yaml': '配置模板',
        '.env.example': '环境变量示例',
    }
    
    for file, desc in required_files.items():
        if os.path.exists(file):
            print(f"  ✓ {file} - {desc}")
        else:
            errors.append(f"缺少文件: {file} ({desc})")
            print(f"  ✗ {file} - 缺失")
    
    # 2. 验证 docker-compose.yml 语法
    print("\n[2/7] 验证 docker-compose.yml 语法...")
    try:
        with open('docker-compose.yml', 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)
        
        # 检查必需字段
        assert 'services' in compose_config, "缺少 services 字段"
        assert 'archivebot' in compose_config['services'], "缺少 archivebot 服务"
        
        service = compose_config['services']['archivebot']
        assert 'build' in service, "缺少 build 配置"
        assert 'volumes' in service, "缺少 volumes 配置"
        assert 'restart' in service, "缺少 restart 配置"
        
        print(f"  ✓ YAML 语法正确")
        print(f"  ✓ 服务名称: archivebot")
        print(f"  ✓ 重启策略: {service['restart']}")
        print(f"  ✓ 挂载卷数: {len(service['volumes'])}")
        
    except Exception as e:
        errors.append(f"docker-compose.yml 错误: {e}")
        print(f"  ✗ 语法错误: {e}")
    
    # 3. 验证 Dockerfile
    print("\n[3/7] 验证 Dockerfile...")
    try:
        with open('Dockerfile', 'r', encoding='utf-8') as f:
            dockerfile_content = f.read()
        
        # 检查关键指令
        checks = {
            'FROM python:3.11': '基础镜像',
            'WORKDIR /app': '工作目录',
            'COPY requirements.txt': '复制依赖文件',
            'RUN pip install': '安装依赖',
            'CMD ["python", "main.py"]': '启动命令',
        }
        
        for check, desc in checks.items():
            if check in dockerfile_content:
                print(f"  ✓ {desc}: 正确")
            else:
                errors.append(f"Dockerfile 缺少: {check}")
                print(f"  ✗ {desc}: 缺失")
                
    except Exception as e:
        errors.append(f"Dockerfile 错误: {e}")
        print(f"  ✗ 读取失败: {e}")
    
    # 4. 验证路径一致性
    print("\n[4/7] 验证路径一致性...")
    try:
        volumes = compose_config['services']['archivebot']['volumes']
        expected_volumes = [
            './data:/app/data',
            './config:/app/config'
        ]
        
        for vol in expected_volumes:
            if vol in volumes:
                host, container = vol.split(':')
                print(f"  ✓ {host} → {container}")
            else:
                errors.append(f"缺少挂载卷: {vol}")
                print(f"  ✗ 缺少: {vol}")
                
    except Exception as e:
        errors.append(f"路径验证失败: {e}")
    
    # 5. 检查 .gitignore 配置
    print("\n[5/7] 检查 .gitignore 配置...")
    try:
        with open('.gitignore', 'r', encoding='utf-8') as f:
            gitignore = f.read()
        
        sensitive_files = [
            'config/config.yaml',
            '.env',
        ]
        
        for file in sensitive_files:
            if file in gitignore:
                print(f"  ✓ {file} - 已排除")
            else:
                warnings.append(f"敏感文件未排除: {file}")
                print(f"  ⚠ {file} - 未排除")
                
    except Exception as e:
        warnings.append(f".gitignore 检查失败: {e}")
    
    # 6. 验证环境变量支持
    print("\n[6/7] 验证环境变量支持...")
    try:
        sys.path.insert(0, '.')
        os.environ['BOT_TOKEN'] = 'test_token_12345'
        os.environ['OWNER_ID'] = '99999'
        
        from src.utils.config import Config
        config = Config()
        
        if config.get('bot.token') == 'test_token_12345':
            print(f"  ✓ BOT_TOKEN 环境变量读取成功")
        else:
            errors.append("BOT_TOKEN 环境变量读取失败")
            
        if config.get('bot.owner_id') == 99999:
            print(f"  ✓ OWNER_ID 环境变量读取成功（类型转换正确）")
        else:
            errors.append("OWNER_ID 环境变量读取失败")
            
        # 清理测试环境变量
        del os.environ['BOT_TOKEN']
        del os.environ['OWNER_ID']
        
    except Exception as e:
        errors.append(f"环境变量支持测试失败: {e}")
        print(f"  ✗ 测试失败: {e}")
    
    # 7. 检查目录结构
    print("\n[7/7] 检查目录结构...")
    required_dirs = ['data', 'config', 'src']
    for dir_name in required_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            print(f"  ✓ {dir_name}/ 目录存在")
        else:
            warnings.append(f"目录不存在: {dir_name}")
            print(f"  ⚠ {dir_name}/ 目录不存在（将在容器中自动创建）")
    
    # 总结
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    if not errors and not warnings:
        print("\n✅ 所有检查通过！Docker 配置完全正确。")
        print("\n用户可以直接使用以下命令部署：")
        print("  1. cp config/config.template.yaml config/config.yaml")
        print("  2. 编辑 config/config.yaml 填写配置")
        print("  3. docker-compose up -d --build")
        return 0
    
    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误：")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告：")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if errors:
        print("\n❌ 配置存在错误，需要修复！")
        return 1
    else:
        print("\n✅ 配置正确，警告不影响使用。")
        return 0


if __name__ == '__main__':
    sys.exit(test_docker_config())
