if __name__ == "__main__":
    import os

    total = 0
    for root, dirs, files in os.walk("data"):
        for filename in files:
            path = os.path.join(root, filename)
            total += os.path.getsize(path)

    db_size = os.path.getsize("players.db")

    print("Total Data: {total_mb} MB".format(total_mb=round(total / (1024 * 1024), 2)))
    print(f"Total Db size: {round(db_size / (1024 * 1024), 2)} MB")
