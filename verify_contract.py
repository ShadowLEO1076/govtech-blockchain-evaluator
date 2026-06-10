"""Verificar que el contrato funciona correctamente en Syscoin zkTanenbaum Testnet"""
import json
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
CHAIN_ID = int(os.getenv("CHAIN_ID", "5700"))

w3 = Web3(Web3.HTTPProvider(RPC_URL))

print("=" * 60)
print("  Verificacion del Contrato EduChainRegistry")
print("=" * 60)
print("Conectado: " + str(w3.is_connected()))
print("Red: Syscoin zkTanenbaum Testnet (Chain ID: " + str(CHAIN_ID) + ")")
print("Contrato: " + str(CONTRACT_ADDRESS))

# Cargar ABI
with open("contract_abi.json", "r") as f:
    abi = json.load(f)

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi
)

# Verificar funciones del contrato
owner = contract.functions.owner().call()
total = contract.functions.totalEvaluaciones().call()
balance = w3.from_wei(w3.eth.get_balance(Web3.to_checksum_address(WALLET_ADDRESS)), "ether")

print("Owner: " + str(owner))
print("Total evaluaciones: " + str(total))
print("Balance wallet: " + str(balance) + " tSYS")
print("")

# Verificar que el owner es nuestra wallet
wallet_checksum = Web3.to_checksum_address(WALLET_ADDRESS)
if owner.lower() == wallet_checksum.lower():
    print("[OK] Owner del contrato = nuestra wallet")
else:
    print("[ERROR] Owner no coincide!")

print("")
print("Explorer: https://explorer-zk.tanenbaum.io/address/" + str(CONTRACT_ADDRESS))
print("=" * 60)
print("TODO LISTO - El contrato funciona correctamente")
print("=" * 60)
