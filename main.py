import os
import csv
import time
import random
from data import *
from config import *
from web3 import Web3
from termcolor import cprint

class ZoraBridger:
    def __init__(self, eth_rpc, zora_contract_address, zora_abi):
        self.web3_eth = Web3(Web3.HTTPProvider(eth_rpc))
        self.bridge_contract = self.web3_eth.eth.contract(address=Web3.toChecksumAddress(zora_contract_address), abi=zora_abi)

    def read_private_keys(self, file_path):
        with open(file_path, "r") as file:
            private_keys = [line.strip() for line in file if line.strip()]
        return private_keys

    def create_transaction_data(self, private_key, to_address, value=None):
        account = self.web3_eth.eth.account.privateKeyToAccount(private_key)
        eth_amount = round(random.uniform(eth_min_amount, eth_max_amount), eth_decimals)
        
        if value is None:
            value = eth_amount

        current_gas_price = self.web3_eth.eth.gasPrice
        max_fee_per_gas = current_gas_price + self.web3_eth.toWei(10, "gwei")
        max_priority_fee_per_gas = self.web3_eth.toWei(0.1, "gwei") 

        #depositTransaction
        data = self.bridge_contract.functions.depositTransaction(
            self.web3_eth.toChecksumAddress(account.address),  # _to
            self.web3_eth.toWei(value, "ether"),  # _value
            100000,  # _gasLimit
            False,   # _isCreation
            b"",     # _data
        ).buildTransaction({
            "chainId": 1,
            "maxFeePerGas": max_fee_per_gas,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "nonce": self.web3_eth.eth.getTransactionCount(account.address),
            "value": self.web3_eth.toWei(value, "ether"),
        })

        return account, data, eth_amount

    def send_transaction(self, account, data, wallet_index, eth_amount):
        signed_transaction = account.signTransaction(data)
        try:
            tx_hash = self.web3_eth.eth.sendRawTransaction(signed_transaction.rawTransaction)
            receipt = self.web3_eth.eth.waitForTransactionReceipt(tx_hash)
            
            if receipt["status"] == 1:
                cprint(f">>>[{wallet_index}] {account.address} {eth_amount} ETH отправлен успешно", "green")
                return receipt
            else:
                cprint(f">>>[{wallet_index}] ({account.address}) Transaction Failed (статус: {receipt['status']})", "red")
                return None
                
        except Exception as e:
            cprint(f">>>[{wallet_index}] ({account.address}) Произошла ошибка при отправке {eth_amount} ETH: {str(e)}", "red")
            return None


RESULTS_DIR = "results"


def record_failed_to_csv(private_key, address, eth_amount):
    results_path = os.path.join(RESULTS_DIR, "failed.csv")
    with open(results_path, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([private_key, address, eth_amount])


def record_success_to_csv(private_key, address, eth_amount):
    results_path = os.path.join(RESULTS_DIR, "success.csv")
    with open(results_path, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([private_key, address, eth_amount])


def main():
    cprint(text1, "cyan")
    cprint(text2, "magenta")
    time.sleep(3)
    bridger = ZoraBridger(eth_rpc, zora_contract_address, zora_abi)

    private_keys = bridger.read_private_keys("keys.txt")

    if not private_keys:
        cprint("Отсутствуют приватные ключи. Завершаю работу.", "red")
        return

    if shuffle:
        random.shuffle(private_keys)

    if not os.path.exists(RESULTS_DIR):
        os.mkdir(RESULTS_DIR)

    for i, private_key in enumerate(private_keys, start=1):

        account, tx_data, eth_amount = bridger.create_transaction_data(private_key, zora_contract_address)

        current_gas_price = bridger.web3_eth.toWei(max_gwei, "gwei")
        gas_check_attempts = 0

        while bridger.web3_eth.eth.gasPrice > current_gas_price:
            gas_check_attempts += 1
            if gas_check_attempts > max_gas_check_attempts:
                print(f"Достигнуто максимальное количество попыток({max_gas_check_attempts}). Завершаю работу...")
                return

            print(f"Попытки {gas_check_attempts}: Gwei ({bridger.web3_eth.fromWei(bridger.web3_eth.eth.gasPrice, 'gwei')}) Выше чем максимально допустимый ({max_gwei} gwei). Сплю...")
            time.sleep(10)

        receipt = bridger.send_transaction(account, tx_data, i, eth_amount)
        if receipt is None:
            record_failed_to_csv(private_key, account.address, eth_amount)
            continue


        record_success_to_csv(private_key, account.address, eth_amount)

        delay = random.randint(min_delay, max_delay)
        time.sleep(delay)

    cprint(text3, "magenta")

if __name__ == "__main__":
    main()
