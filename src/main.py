while True:
    try:
        user_input=int(input("Enter your Choice:"))
        if user_input==1:
            print("inventory")
        elif user_input==2:
            print("billing")
        elif user_input==3:
            print("report")
        elif user_input==4:
            print("Exit")
            break
        else:
            print("invalid choice")
    except ValueError:
        print("invalid input")