"""NSE 스크립트 자동 선택 모듈"""


def select_nse_scripts(ports: str) -> str:
    """
    포트 목록을 기반으로 적절한 NSE 스크립트 선택

    Args:
        ports: 쉼표로 구분된 포트 목록 (예: "22,80,443,3306")

    Returns:
        nmap --script 옵션에 사용할 스크립트 표현식

    Examples:
        >>> select_nse_scripts("22,80,443")
        '((ssh-hostkey or ssh-auth-methods) or (http-title or ...) or ...) and (safe or ...)'
        >>> select_nse_scripts("9999")
        'vuln and safe'
    """
    port_list = [p.strip() for p in ports.split(",") if p.strip()]
    port_set = set(port_list)

    script_parts = []

    # HTTP
    if "80" in port_set or "8080" in port_set:
        script_parts.append(
            "(http-title or http-server-header or http-methods or "
            "http-robots.txt or http-headers or http-enum or http-vuln-*)"
        )

    # HTTPS
    if "443" in port_set or "8443" in port_set:
        script_parts.append(
            "(ssl-cert or ssl-date or ssl-heartbleed or ssl-poodle or "
            "ssl-dh-params or ssl-enum-ciphers)"
        )
        # HTTPS만 있고 HTTP가 없으면 HTTP 정보 스크립트 추가
        if "80" not in port_set and "8080" not in port_set:
            script_parts.append("(http-title or http-server-header)")

    # MySQL
    if "3306" in port_set:
        script_parts.append(
            "(mysql-info or mysql-audit or mysql-empty-password)"
        )

    # MS-SQL
    if "1433" in port_set:
        script_parts.append(
            "(ms-sql-info or ms-sql-ntlm-info or ms-sql-empty-password)"
        )

    # MongoDB
    if "27017" in port_set:
        script_parts.append("(mongodb-info or mongodb-databases)")

    # PostgreSQL
    if "5432" in port_set:
        script_parts.append("(pgsql-brute or postgresql-info)")

    # SSH
    if "22" in port_set:
        script_parts.append("(ssh-hostkey or ssh-auth-methods)")

    # RDP
    if "3389" in port_set:
        script_parts.append(
            "(rdp-enum-encryption or rdp-ntlm-info or rdp-vuln-ms12-020)"
        )

    # VNC
    if "5900" in port_set:
        script_parts.append("(vnc-info or vnc-title)")

    # SAP
    if any(p in port_set for p in ["3200", "3300", "8000", "50000"]):
        script_parts.append("(http-sap-netweaver-leak)")

    # SMB
    if "445" in port_set:
        script_parts.append("(smb-os-discovery or smb-vuln-*)")

    # FTP
    if "21" in port_set:
        script_parts.append("(ftp-anon or ftp-syst or ftp-vuln-*)")

    # Telnet
    if "23" in port_set:
        script_parts.append("(telnet-encryption or telnet-ntlm-info)")

    # 브루트포스 스크립트 (별도 처리 - phase4에서 조건부 실행)
    # 여기서는 일반 취약점 스캔 스크립트만 반환

    # 스크립트가 하나도 없으면 기본 취약점 스캔
    if not script_parts:
        return "vuln and safe"

    # 모든 스크립트 OR 연산자로 결합
    combined = " or ".join(script_parts)

    # 안전성 필터 추가
    return f"({combined}) and (safe or (discovery and not intrusive) or (vuln and safe))"


def should_run_bruteforce(ports: str, service: str) -> bool:
    """
    특정 서비스에 브루트포스를 실행해야 하는지 판단

    Args:
        ports: 쉼표로 구분된 포트 목록
        service: 서비스 이름 ("ftp", "ssh", "telnet")

    Returns:
        브루트포스 실행 여부
    """
    port_set = set(p.strip() for p in ports.split(",") if p.strip())

    service_port_map = {
        "ftp": "21",
        "ssh": "22",
        "telnet": "23",
    }

    return service_port_map.get(service) in port_set
