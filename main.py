from colorama import init, Fore, Back, Style
from termcolor import colored


def main():
    print(colored("||                       Basic Shopify Bot                      ||", "white"))
    print(colored("----------------------------- V0.0.1 -----------------------------", "yellow"))
    print(colored("Choose option:", "magenta"))
    print(colored("1. Shopify Frontend Checkout (Safe Modes)", "blue"))
    print(colored("2. Shopify Backend Checkout (Fast Modes)", "blue"))
    #shop = shopify.shopifyMain()
    userInput = input()
    if userInput == "1":
        import scripts.normalShopify as shopify
        shop = shopify.shopifyMain()
    elif userInput.strip() == "2":
        print(colored("Coming Soon :)", "yellow"))
        pass

if __name__ == "__main__":
    main()
