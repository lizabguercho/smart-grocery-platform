from pathlib import Path


def main()-> None:
    data_folder = Path("data/raw/shufersal")
    price_full_files = sorted(data_folder.glob("*PriceFull*"))
    print(f"Found {len(price_full_files)} PriceFull files:\n")

    for file in price_full_files:
        print(file.name) 

if __name__ == "__main__":
    main()
    
