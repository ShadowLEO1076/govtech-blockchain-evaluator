"""
Deploy EduChainRegistry.sol en Syscoin Tanenbaum Testnet
Red: Syscoin Tanenbaum NEVM Testnet
Chain ID: 5700
RPC: https://rpc.tanenbaum.io
Explorer: https://tanenbaum.io
"""

import json
import os
import sys
import time
from dotenv import load_dotenv
from web3 import Web3
from solcx import compile_standard, install_solc

# --- Cargar variables ---
load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
RPC_URL = os.getenv("RPC_URL", "https://rpc.tanenbaum.io")
CHAIN_ID = int(os.getenv("CHAIN_ID", "5700"))

print("=" * 60)
print("  EduChain Registry - Deploy en Syscoin Tanenbaum Testnet")
print("=" * 60)
print(f"  RPC:      {RPC_URL}")
print(f"  Chain ID: {CHAIN_ID}")
print(f"  Wallet:   {WALLET_ADDRESS}")
print("=" * 60)

# --- Conectar ---
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60}))

if not w3.is_connected():
    print("ERROR: No se pudo conectar al nodo RPC")
    sys.exit(1)

print(f"[OK] Conectado a Syscoin Tanenbaum Testnet (Chain ID: {CHAIN_ID})")

# --- Verificar balance ---
wallet = Web3.to_checksum_address(WALLET_ADDRESS)
balance = w3.eth.get_balance(wallet)
balance_ether = w3.from_wei(balance, "ether")
print(f"[OK] Balance: {balance_ether} tSYS")

if balance == 0:
    print("ERROR: No tienes fondos.")
    sys.exit(1)

# --- Leer contrato ---
contract_path = os.path.join(os.path.dirname(__file__), "contracts", "EduChainRegistry.sol")
with open(contract_path, "r", encoding="utf-8") as f:
    source_code = f.read()

print("[OK] Contrato leido: EduChainRegistry.sol")

# --- Compilar ---
print("[...] Instalando compilador Solidity 0.8.20...")
install_solc("0.8.20")

print("[...] Compilando contrato...")
compiled = compile_standard(
    {
        "language": "Solidity",
        "sources": {
            "EduChainRegistry.sol": {"content": source_code}
        },
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                }
            },
            "optimizer": {"enabled": True, "runs": 200},
        },
    },
    solc_version="0.8.20",
)

contract_data = compiled["contracts"]["EduChainRegistry.sol"]["EduChainRegistry"]
abi = contract_data["abi"]
bytecode = contract_data["evm"]["bytecode"]["object"]

print("[OK] Compilacion exitosa")

# Guardar ABI
abi_path = os.path.join(os.path.dirname(__file__), "contract_abi.json")
with open(abi_path, "w") as f:
    json.dump(abi, f, indent=2)
print("[OK] ABI guardado en contract_abi.json")

# --- Desplegar ---
print("[...] Desplegando en Syscoin Tanenbaum Testnet...")

contract = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(wallet)

# Usar gas price mas alto para que se mine rapido
gas_price = w3.eth.gas_price
# Usar al menos 10 gwei para asegurar que se mine
min_gas_price = w3.to_wei(10, "gwei")
if gas_price < min_gas_price:
    gas_price = min_gas_price

print(f"[INFO] Gas price: {w3.from_wei(gas_price, 'gwei')} Gwei")
print(f"[INFO] Nonce: {nonce}")

tx = contract.constructor().build_transaction(
    {
        "from": wallet,
        "nonce": nonce,
        "gas": 2000000,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    }
)

signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print(f"[TX] Transaccion enviada: 0x{tx_hash.hex()}")
print(f"[...] Esperando confirmacion (timeout: 600s)...")

# Esperar con timeout largo y reportar progreso
start_time = time.time()
receipt = None
timeout = 600  # 10 minutos

while time.time() - start_time < timeout:
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt is not None:
            break
    except Exception:
        pass
    elapsed = int(time.time() - start_time)
    if elapsed % 30 == 0 and elapsed > 0:
        print(f"[...] {elapsed}s transcurridos, esperando confirmacion...")
    time.sleep(5)

if receipt is None:
    print(f"TIMEOUT: La transaccion no se confirmo en {timeout}s")
    print(f"Tx Hash: 0x{tx_hash.hex()}")
    print("Puedes verificar manualmente en: https://tanenbaum.io")
    sys.exit(1)

if receipt.status == 1:
    contract_address = receipt.contractAddress
    print("")
    print("=" * 60)
    print("  CONTRATO DESPLEGADO EXITOSAMENTE!")
    print("=" * 60)
    print(f"  Contract Address: {contract_address}")
    print(f"  Block Number:     {receipt.blockNumber}")
    print(f"  Gas Used:         {receipt.gasUsed}")
    print(f"  Explorer:")
    print(f"     https://tanenbaum.io/address/{contract_address}")
    tx_hex = tx_hash.hex()
    print(f"  Tx:")
    print(f"     https://tanenbaum.io/tx/0x{tx_hex}")
    print("=" * 60)

    # Auto-actualizar .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r") as f:
        env_content = f.read()

    env_content = env_content.replace(
        'CONTRACT_ADDRESS="PENDIENTE_DESPLEGAR"',
        f'CONTRACT_ADDRESS="{contract_address}"'
    )
    env_content = env_content.replace(
        'CONTRACT_ADDRESS="0xd9145CCE52D386f254917e481eB44e9943F39138"',
        f'CONTRACT_ADDRESS="{contract_address}"'
    )

    with open(env_path, "w") as f:
        f.write(env_content)

    print("[OK] .env actualizado automaticamente")
    print(f"Contrato listo: {contract_address}")

else:
    print("ERROR: La transaccion fallo")
    print(f"Tx Hash: 0x{tx_hash.hex()}")
    sys.exit(1)
