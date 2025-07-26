from datetime import datetime, timedelta

# def time_calculator(time_start:str,time_end:str) -> str:


#     hour_start_time , minute_start_time = convert_to_number(time_start)
#     hour_end_time , minute_end_time = convert_to_number(time_end)


def convert_to_number(time_str: str) -> tuple[int, int, int]:
    time_temp = 0
    time_list = []
    temp_index = 0
    over_carry_count = 0
    separator = [",", ";", " ", ":", ",", "-", "."]
    time_str = time_str.strip()
    contains_separator = any(sep in time_str for sep in separator)
    if contains_separator:
        for sep in separator:
            time_str = time_str.replace(sep, ":")
        for letters in time_str[::-1]:
            if letters.isdigit():
                time_temp += int(letters) * (10**temp_index)
                temp_index += 1
            elif letters == ":":
                time_list.append(time_temp)
                time_temp = 0
                temp_index = 0
        time_list.append(time_temp)
    elif time_str.isdigit():
        for letters in time_str[::-1]:
            if temp_index < 2:
                time_temp += int(letters) * (10**temp_index)
                temp_index += 1
            else:
                time_list.append(time_temp)
                time_temp = int(letters)
                temp_index = 1
        time_list.append(time_temp)
    while len(time_list) < 3:
        time_list.append(0)
    while len(time_list) > 3:
        time_list.pop()
    # print(time_list)
    for index, item in enumerate(time_list):
        if index == 2:
            time_list[index] = item + over_carry_count
        else:
            time_list[index] = item % 60 + over_carry_count
            over_carry_count = item // 60
    return time_list[2], time_list[1], time_list[0]


def time_difference(first_time: str, last_time: str) -> tuple[int, int, int]:
    first_time_tuple = convert_to_number(first_time)
    last_time_tuple = convert_to_number(last_time)
    first_time_delta = timedelta(
        hours=first_time_tuple[0],
        minutes=first_time_tuple[1],
        seconds=first_time_tuple[2],
    )
    last_time_delta = timedelta(
        hours=last_time_tuple[0], minutes=last_time_tuple[1], seconds=last_time_tuple[2]
    )
    diff = abs(last_time_delta - first_time_delta)
    return diff.seconds // 3600, (diff.seconds // 60) % 60, diff.seconds % 60


print(time_difference("00 20 09", "00 19 48"))  # Example usage

