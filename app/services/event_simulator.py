
import random

COMMON_PORTS = [80, 443, 22, 3306, 5432, 21, 25, 8080, 53, 3389]
ADMIN_PORTS = [22, 3306, 3389, 21]


def _random_ip(internal: bool = False) -> str:
    if internal:
        return f"192.168.{random.randint(0, 5)}.{random.randint(1, 254)}"
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def generate_normal_event() -> dict:
    return {
        "src_ip": _random_ip(internal=True),
        "dst_ip": _random_ip(internal=random.random() < 0.4),
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice(COMMON_PORTS),
        "protocol": random.choices(["TCP", "UDP", "ICMP"], [0.75, 0.20, 0.05])[0],
        "bytes_sent": max(0, random.gauss(4000, 1500)),
        "bytes_received": max(0, random.gauss(15000, 6000)),
        "packet_count": max(1, int(random.gauss(40, 15))),
        "duration_ms": max(10, random.gauss(800, 400)),
        "connection_rate": max(0.1, random.gauss(2, 1)),
    }


def generate_port_scan_event() -> dict:
    attacker_ip = _random_ip()
    return {
        "src_ip": attacker_ip,
        "dst_ip": _random_ip(internal=True),
        "src_port": random.randint(1024, 65535),
        "dst_port": random.randint(1, 65535),
        "protocol": "TCP",
        "bytes_sent": max(0, random.gauss(60, 20)),
        "bytes_received": max(0, random.gauss(40, 15)),
        "packet_count": max(1, int(random.gauss(3, 1))),
        "duration_ms": max(1, random.gauss(15, 8)),
        "connection_rate": max(20, random.gauss(80, 25)),
    }


def generate_brute_force_event() -> dict:
    attacker_ip = _random_ip()
    return {
        "src_ip": attacker_ip,
        "dst_ip": _random_ip(internal=True),
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice(ADMIN_PORTS),
        "protocol": "TCP",
        "bytes_sent": max(0, random.gauss(200, 50)),
        "bytes_received": max(0, random.gauss(150, 40)),
        "packet_count": max(1, int(random.gauss(6, 2))),
        "duration_ms": max(5, random.gauss(50, 20)),
        "connection_rate": max(15, random.gauss(60, 20)),
    }


def generate_ddos_event(target_ip: str, target_port: int) -> dict:
    # target_ip/port sengaja dilempar dari luar (fixed per simulasi),
    # soalnya ciri khas DDoS itu BANYAK src beda-beda nembak 1 target yang sama
    return {
        "src_ip": _random_ip(),
        "dst_ip": target_ip,
        "src_port": random.randint(1024, 65535),
        "dst_port": target_port,
        "protocol": random.choices(["TCP", "UDP"], [0.5, 0.5])[0],
        "bytes_sent": max(0, random.gauss(100, 40)),
        "bytes_received": max(0, random.gauss(10, 5)),
        "packet_count": max(1, int(random.gauss(150, 50))),
        "duration_ms": max(1, random.gauss(20, 10)),
        "connection_rate": max(50, random.gauss(200, 60)),
    }


def generate_data_exfiltration_event() -> dict:
    return {
        "src_ip": _random_ip(internal=True),
        "dst_ip": _random_ip(internal=False),
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice([443, 21, 22, 8080]),
        "protocol": "TCP",
        "bytes_sent": max(0, random.gauss(500_000, 150_000)),
        "bytes_received": max(0, random.gauss(2000, 800)),
        "packet_count": max(1, int(random.gauss(400, 100))),
        "duration_ms": max(100, random.gauss(60_000, 20_000)),
        "connection_rate": max(0.1, random.gauss(1, 0.5)),
    }