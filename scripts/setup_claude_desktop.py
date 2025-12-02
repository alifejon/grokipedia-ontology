#!/usr/bin/env python3
"""
Claude Desktop MCP 서버 설정 스크립트

이 스크립트는 Grokipedia Ontology MCP 서버를 Claude Desktop에
자동으로 설정합니다.

사용법:
    python scripts/setup_claude_desktop.py /path/to/data.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path


def get_claude_config_path() -> Path:
    """운영체제에 따른 Claude Desktop 설정 파일 경로를 반환합니다."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            raise RuntimeError("APPDATA 환경 변수를 찾을 수 없습니다.")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_command_path() -> str:
    """grokipedia-ontology 명령어의 전체 경로를 찾습니다."""
    # 시스템 PATH에서 찾기
    cmd = shutil.which("grokipedia-ontology")
    if cmd:
        return cmd

    # pip으로 설치된 경로 찾기
    try:
        import grokipedia_ontology
        module_path = Path(grokipedia_ontology.__file__).parent.parent.parent
        possible_paths = [
            module_path / "bin" / "grokipedia-ontology",
            Path(sys.prefix) / "bin" / "grokipedia-ontology",
            Path(sys.prefix) / "Scripts" / "grokipedia-ontology.exe",  # Windows
        ]
        for p in possible_paths:
            if p.exists():
                return str(p)
    except ImportError:
        pass

    # 찾지 못한 경우 기본값 반환
    return "grokipedia-ontology"


def load_existing_config(config_path: Path) -> dict:
    """기존 설정 파일을 로드합니다."""
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️  기존 설정 파일이 손상되었습니다. 백업 후 새로 생성합니다.")
            backup_path = config_path.with_suffix(".json.backup")
            shutil.copy(config_path, backup_path)
            print(f"   백업 위치: {backup_path}")
    return {}


def create_mcp_config(data_path: Path, server_name: str = "grokipedia-ontology") -> dict:
    """MCP 서버 설정을 생성합니다."""
    command = get_command_path()

    return {
        "command": command,
        "args": ["mcp-serve", str(data_path.absolute())],
        "env": {}
    }


def setup_claude_desktop(
    data_path: Path,
    server_name: str = "grokipedia-ontology",
    force: bool = False
) -> None:
    """Claude Desktop에 MCP 서버를 설정합니다."""

    # 데이터 파일 확인
    if not data_path.exists():
        print(f"❌ 데이터 파일을 찾을 수 없습니다: {data_path}")
        sys.exit(1)

    # JSON 형식 검증
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 데이터 파일이 올바른 JSON 형식이 아닙니다: {e}")
        sys.exit(1)

    # 설정 파일 경로
    config_path = get_claude_config_path()
    print(f"📁 설정 파일 경로: {config_path}")

    # 디렉토리 생성
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 기존 설정 로드
    config = load_existing_config(config_path)

    # mcpServers 섹션 초기화
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # 기존 설정 확인
    if server_name in config["mcpServers"] and not force:
        print(f"⚠️  '{server_name}' 서버가 이미 설정되어 있습니다.")
        response = input("덮어쓰시겠습니까? (y/N): ").strip().lower()
        if response != "y":
            print("설정을 취소합니다.")
            return

    # 새 설정 추가
    config["mcpServers"][server_name] = create_mcp_config(data_path, server_name)

    # 설정 저장
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 설정이 완료되었습니다!")
    print(f"\n📋 설정 내용:")
    print(json.dumps(config["mcpServers"][server_name], indent=2, ensure_ascii=False))

    print(f"\n🔄 다음 단계:")
    print("   1. Claude Desktop을 완전히 종료합니다.")
    print("   2. Claude Desktop을 다시 시작합니다.")
    print("   3. 새 대화에서 '지식 그래프 통계를 보여줘'라고 입력해 보세요.")


def verify_installation() -> bool:
    """설치 상태를 확인합니다."""
    print("🔍 설치 상태 확인 중...")

    # 패키지 설치 확인
    try:
        import grokipedia_ontology
        print(f"   ✓ grokipedia-ontology 버전: {grokipedia_ontology.__version__}")
    except ImportError:
        print("   ✗ grokipedia-ontology가 설치되지 않았습니다.")
        print("     설치: pip install grokipedia-ontology[mcp]")
        return False

    # MCP 의존성 확인
    try:
        from grokipedia_ontology.mcp_server import MCP_AVAILABLE
        if MCP_AVAILABLE:
            print("   ✓ MCP 의존성 설치됨")
        else:
            print("   ✗ MCP 의존성이 설치되지 않았습니다.")
            print("     설치: pip install grokipedia-ontology[mcp]")
            return False
    except ImportError:
        print("   ✗ MCP 모듈을 불러올 수 없습니다.")
        return False

    # 명령어 확인
    cmd = shutil.which("grokipedia-ontology")
    if cmd:
        print(f"   ✓ CLI 명령어: {cmd}")
    else:
        print("   ⚠ CLI 명령어를 PATH에서 찾을 수 없습니다.")
        print("     python -m grokipedia_ontology.cli로 실행 가능합니다.")

    return True


def show_current_config() -> None:
    """현재 설정을 표시합니다."""
    config_path = get_claude_config_path()

    if not config_path.exists():
        print(f"📁 설정 파일이 없습니다: {config_path}")
        return

    print(f"📁 설정 파일: {config_path}")
    print()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if "mcpServers" in config:
            print("🔧 등록된 MCP 서버:")
            for name, settings in config["mcpServers"].items():
                print(f"\n   [{name}]")
                print(f"   명령어: {settings.get('command', 'N/A')}")
                print(f"   인자: {' '.join(settings.get('args', []))}")
        else:
            print("등록된 MCP 서버가 없습니다.")

    except json.JSONDecodeError:
        print("❌ 설정 파일을 파싱할 수 없습니다.")


def main():
    parser = argparse.ArgumentParser(
        description="Claude Desktop에 Grokipedia Ontology MCP 서버를 설정합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 데이터 파일로 설정
  python setup_claude_desktop.py /path/to/data.json

  # 설치 상태 확인
  python setup_claude_desktop.py --verify

  # 현재 설정 확인
  python setup_claude_desktop.py --show

  # 강제 덮어쓰기
  python setup_claude_desktop.py /path/to/data.json --force
"""
    )

    parser.add_argument(
        "data_path",
        nargs="?",
        type=Path,
        help="지식 그래프 데이터 파일 경로 (JSON)"
    )

    parser.add_argument(
        "--name",
        default="grokipedia-ontology",
        help="MCP 서버 이름 (기본값: grokipedia-ontology)"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="기존 설정을 확인 없이 덮어쓰기"
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="설치 상태만 확인"
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="현재 설정 표시"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🌐 Grokipedia Ontology - Claude Desktop 설정 도구")
    print("=" * 60)
    print()

    if args.verify:
        verify_installation()
        return

    if args.show:
        show_current_config()
        return

    if not args.data_path:
        parser.print_help()
        print("\n❌ 데이터 파일 경로를 지정해주세요.")
        sys.exit(1)

    # 설치 확인
    if not verify_installation():
        sys.exit(1)

    print()
    setup_claude_desktop(args.data_path, args.name, args.force)


if __name__ == "__main__":
    main()
