from src.build_pdf import main


PERSONAL_DATA = {
    "personal_data": "data/personal_data.json",
    "application": "data/application.json",
    "photo": "data/profile_photo.jpg",
    "signature": "data/signature.png",
    }

PERSONAL_DATA = {
    "personal_data": "application_databank/personal_data.json",
    "application": "application_databank/application.json",
    "photo": "application_databank/profile_photo.jpg",
    "signature": "application_databank/signature.png",
    }

def _build_args_from_personal_data(config: dict[str, str]) -> list[str]:
    args = [
        "--personal-data",
        config["personal_data"],
        "--application",
        config["application"],
        "--cover-letter",
    ]

    photo = config.get("photo")
    if photo:
        args.extend(["--photo", photo])

    signature = config.get("signature")
    if signature:
        args.extend(["--signature", signature])

    return args


if __name__ == "__main__":
    raise SystemExit(main(_build_args_from_personal_data(PERSONAL_DATA)))
