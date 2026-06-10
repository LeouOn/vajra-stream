from kerykeion import AstrologicalSubject


def test():
    subject = AstrologicalSubject(
        "Test", 1990, 5, 15, 14, 30, lng=-0.12, lat=51.5, tz_str="Europe/London", city="London"
    )
    print(subject.sun)
    print("Planets list type:", type(subject.planets_list[0]))
    print(subject.planets_list[0])


if __name__ == "__main__":
    test()
