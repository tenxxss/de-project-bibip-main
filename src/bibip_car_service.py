import os
from models import Car, CarFullInfo, CarStatus, Model, ModelSaleStats, Sale

class CarService:
    def __init__(self, root_directory_path: str) -> None:
        self.root_directory_path = root_directory_path

    def _add(self, data_file: str, index_file: str, key: str, text: str) -> None:
        data_path = os.path.join(self.root_directory_path, data_file)
        index_path = os.path.join(self.root_directory_path, index_file)

        if os.path.exists(data_path):
            row_number = os.path.getsize(data_path) // 501
        else:
            row_number = 0

        with open(data_path, 'a', encoding='utf-8', newline='') as f:
            f.write(text.ljust(500) + '\n')

        with open(index_path, "a", encoding="utf-8", newline='') as f:
            f.write(f"{key};{row_number}\n")

    def add_model(self, model: Model) -> Model:
        self._add('models.txt', 'models_index.txt', model.index(), model.model_dump_json())
        return model

    def add_car(self, car: Car) -> Car:
        self._add('cars.txt', 'cars_index.txt', car.index(), car.model_dump_json())
        return car

    def sell_car(self, sale: Sale) -> Car:
        self._add('sales.txt', 'sales_index.txt', sale.index(), sale.model_dump_json())

        row = self._find_row('cars_index.txt', sale.car_vin)

        cars_path = os.path.join(self.root_directory_path, 'cars.txt')

        with open(cars_path, 'r', encoding='utf-8', newline='') as f:
            f.seek(row * 501)
            row_text = f.read(500).rstrip()

        car = Car.model_validate_json(row_text)

        car.status = CarStatus.sold

        car_json = car.model_dump_json()
        new_json_row = car_json.ljust(500) + '\n'

        with open(cars_path, 'r+', encoding='utf-8', newline='') as f:
            f.seek(row * 501)
            f.write(new_json_row)

        return car

    def _find_row(self, index_file: str, key: str) -> int | None:
        index_path = os.path.join(self.root_directory_path, index_file)

        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8', newline='') as f:
                for line in f:
                    clean_line = line.strip()
                    parts = clean_line.split(';')
                    found_key = parts[0]
                    row = parts[1]

                    if found_key == key:
                        return int(row)

        return None

    def get_cars(self, status: CarStatus) -> list[Car]:
        cars_path = os.path.join(self.root_directory_path, 'cars.txt')
        model_list = []

        with open(cars_path, 'r', encoding='utf-8', newline='') as f:
            for line in f:
                line = line.strip()
                car = Car.model_validate_json(line)
                if car.status == status:
                    model_list.append(car)

        return model_list

    def get_car_info(self, vin: str) -> CarFullInfo | None:
        row = self._find_row('cars_index.txt', vin)
        if row is None:
            return None

        cars_path = os.path.join(self.root_directory_path, 'cars.txt')

        with open(cars_path, 'r', encoding='utf-8', newline='') as f:
            f.seek(row * 501)
            row_text = f.read(500).rstrip()

        car = Car.model_validate_json(row_text)

        model_row = self._find_row('models_index.txt', str(car.model))
        models_path = os.path.join(self.root_directory_path, 'models.txt')

        with open(models_path, 'r', encoding='utf-8', newline='') as f:
            f.seek(model_row * 501)
            model_text = f.read(500).rstrip()

        model = Model.model_validate_json(model_text)
        sale_row = self._find_row('sales_index.txt', vin)

        if sale_row is None:
            sales_date = None
            sales_cost = None
        else:
            sales_path = os.path.join(self.root_directory_path, 'sales.txt')
            with open(sales_path, 'r', encoding='utf-8', newline='') as f:
                f.seek(sale_row * 501)
                sale_text = f.read(500).rstrip()

            sale = Sale.model_validate_json(sale_text)
            sales_date = sale.sales_date
            sales_cost = sale.cost

        return CarFullInfo(
            vin=car.vin,
            car_model_name=model.name,
            car_model_brand=model.brand,
            price=car.price,
            date_start=car.date_start,
            status=car.status,
            sales_date=sales_date,
            sales_cost=sales_cost,
        )

    def update_vin(self, vin: str, new_vin: str) -> Car:
        row = self._find_row('cars_index.txt', vin)

        cars_path = os.path.join(self.root_directory_path, 'cars.txt')

        with open(cars_path, 'r', encoding='utf-8', newline='') as f:
            f.seek(row * 501)
            row_text = f.read(500).rstrip()

        car = Car.model_validate_json(row_text)
        car.vin = new_vin

        vin_json = car.model_dump_json()
        new_json_row = vin_json.ljust(500) + '\n'

        with open(cars_path, 'r+', encoding='utf-8', newline='') as f:
            f.seek(row * 501)
            f.write(new_json_row)

        index_path = os.path.join(self.root_directory_path, 'cars_index.txt')

        with open(index_path, 'r', encoding='utf-8', newline='') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            clean_line = line.strip()
            key, line_row = clean_line.split(';')
            if key == vin:
                new_lines.append(f"{new_vin};{line_row}\n")
            else:
                new_lines.append(line)

        with open(index_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)

        return car

    def revert_sale(self, sales_number: str) -> Car:
        sales_path = os.path.join(self.root_directory_path, 'sales.txt')

        sale = None
        sale_row = None
        with open(sales_path, 'r', encoding='utf-8', newline='') as f:
            for current_row, line in enumerate(f):
                clean_line = line.strip()
                candidate = Sale.model_validate_json(clean_line)
                if candidate.sales_number == sales_number:
                    sale = candidate
                    sale_row = current_row
                    break

        if sale is None:
            raise ValueError(f"Продажа с номером {sales_number!r} не найдена")

        active_row = self._find_row('sales_index.txt', sale.car_vin)
        if active_row != sale_row:
            raise ValueError(f"Продажа с номером {sales_number!r} уже отменена")

        car_row = self._find_row('cars_index.txt', sale.car_vin)
        car_path = os.path.join(self.root_directory_path, 'cars.txt')

        with open(car_path, 'r', encoding='utf-8', newline='') as f:
            f.seek(car_row * 501)
            car_text = f.read(500).rstrip()

        car = Car.model_validate_json(car_text)
        car.status = CarStatus.available
        car_json = car.model_dump_json()
        new_json_row = car_json.ljust(500) + '\n'

        with open(car_path, 'r+', encoding='utf-8', newline='') as f:
            f.seek(car_row * 501)
            f.write(new_json_row)

        index_path = os.path.join(self.root_directory_path, 'sales_index.txt')
        with open(index_path, 'r', encoding='utf-8', newline='') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            clean_line = line.strip()
            key, _ = clean_line.split(';')

            if key != sale.car_vin:
                new_lines.append(line)

        with open(index_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)

        return car

    def top_models_by_sales(self) -> list[ModelSaleStats]:
        sales_path = os.path.join(self.root_directory_path, 'sales.txt')
        cars_path = os.path.join(self.root_directory_path, 'cars.txt')
        models_path = os.path.join(self.root_directory_path, 'models.txt')

        stats = {}

        if os.path.exists(sales_path):
            with open(sales_path, 'r', encoding='utf-8', newline='') as f:
                for line in f:
                    line_text = line.strip()
                    if not line_text:
                        continue
                    sale = Sale.model_validate_json(line_text)

                    car_row = self._find_row('cars_index.txt', sale.car_vin)
                    if car_row is None:
                        continue

                    with open(cars_path, 'r', encoding='utf-8', newline='') as f:
                        f.seek(car_row * 501)
                        car_text = f.read(500).rstrip()

                    car = Car.model_validate_json(car_text)
                    model_id = str(car.model)

                    if model_id not in stats:
                        stats[model_id] = {'count': 0, 'price': car.price}

                    stats[model_id]['count'] += 1

                    if car.price > stats[model_id]['price']:
                        stats[model_id]['price'] = car.price

        result_list = []
        for model_id, info in stats.items():
            model_row = self._find_row('models_index.txt', model_id)
            if model_row is None:
                continue

            with open(models_path, 'r', encoding='utf-8', newline='') as f:
                f.seek(model_row * 501)
                model_text = f.read(500).rstrip()

            model = Model.model_validate_json(model_text)

            stats_obj = ModelSaleStats(
                car_model_name=model.name,
                brand=model.brand,
                sales_number=info['count']
            )

            result_list.append((stats_obj, info['count'], info['price']))
        result_list.sort(key=lambda x: (-x[1], -x[2]))

        return [item[0] for item in result_list[:3]]