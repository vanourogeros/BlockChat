import argparse
import requests
import json
import os


def new_transaction(args, base_address):
    data = {
            "sender_address": f"{args.address}",
            "receiver_address": args.receiver_address,
            "amount": args.amount,
            "type": "coins",
            "message": ""
        }
    payload = json.dumps(data)
    print(f"{base_address}/make_transaction")
    response = requests.post(f"{base_address}/make_transaction", data=payload, headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        print("Error:", response)
        return
    print("Transaction was successful")
    print(response)

def new_message(args, base_address):
    data = {
            "sender_address": f"{args.address}",
            "receiver_address": args.receiver_address,
            "amount": 0,
            "type": "message",
            "message": args.message
        }
    payload = json.dumps(data)
    response = requests.post(f"{base_address}/make_transaction", data=payload, headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        print("Error:", response)
        return
    print("Message was successful")
    print(response)

def stake():
    pass

def view(base_address):
    response = requests.get(f"{base_address}/view_block",  headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        print("Error:", response)
        return
    data = response.json()
    print("Validator id :", data['validator'])
    print('Transactions :')
    for tran in data["transactions"]:
        print(tran)


def balance():
    pass

def help():
    print("Usage:")
    print("  t <recipient_address> <amount>  : New transaction")
    print("  m <recipient_address> <message> : New message")
    print("  stake <amount>                  : Set the node stake")
    print("  view                            : View last block")
    print("  balance                         : Show balance")

def main():
    parser = argparse.ArgumentParser(description='CLI app for the BlockChat system')
    parser.add_argument("--address", type=str, help="Node address")

    subparsers = parser.add_subparsers(dest='command', help='sub-command help')

    parser_t = subparsers.add_parser('t', help='New transaction')
    parser_t.add_argument('<receiver_address>', type=str, help='Recipient address')
    parser_t.add_argument('<amount>', type=int, help='Amount to send')

    parser_m = subparsers.add_parser('m', help='New message')
    parser_m.add_argument('<receiver_address>', type=str, help='Recipient address')
    parser_m.add_argument('<message>', type=str, help='Message to send')

    parser_v = subparsers.add_parser('view', help='View last block')

    parser_h = subparsers.add_parser('help', help='Show help')

    args = parser.parse_args()

    base_address = f'http://{args.address}/api'

    if args.command == 't':
        new_transaction(args, base_address)
    elif args.command == 'm': # we assume that for a new message the command is "m"
        new_message(args, base_address)
    elif args.command == 'help' or args.command is None:
        help()
    elif args.command == 'view':
        BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")  # 127.0.0.1
        BOOTSTRAP_PORT = int(os.getenv("BOOTSTRAP_PORT"))
        view('http://' + BOOTSTRAP_IP+':'+str(BOOTSTRAP_PORT)+'/api')
    else:
        print('Invalid command')

if __name__ == '__main__':
    main()
