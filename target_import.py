import json
import requests
import csv
import sys
from datetime import datetime


class TradeGecko:
    def __init__(self):
        self.temp_config = {
            "api_id": "864328133aa12027bd01949fed653aaba6e35ac1cffd67987da7715978cebb94",
            "api_secret": "0LjRQKKwSqb7xEGExkXms_y_IcL4lDEpefkvdxM2Yoc",
            "api_token": "5qjU8HQ_dzHk4M1Fdl7QE98UVYXqf19NzSdSJhPSO6o"
        }

#Old Api token
#r_EBYvVD--qniR4ygb6_m6x5a1xqmJNEBDefe2LJ-_A

#New API token
# 5qjU8HQ_dzHk4M1Fdl7QE98UVYXqf19NzSdSJhPSO6o	
    def request(self, mode, endpoint, params=None, data=None):  # module for making requests against the Cin7 API

        # mode = API request method (GET, POST, PUT, DELETE), must be a string
        # endpoint = destination for request (ie. accounts, orders, variants)
        # params = extra parameters to include in request URL, object should be a dict
        # data = payload to pass to endpoint (for POST & PUT), object should be a dict

        url = "https://api.tradegecko.com/" + endpoint

        if data:  # converts payload dict to JSON string
            payload = json.dumps(data)

        s = requests.Session()  # initialise session

        auth = "Bearer " + self.temp_config["api_token"]  # concatenate token into Bearer token

        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Marketplace Order Import for EM Brands",
            "Authorization": auth
        }

        s.headers.update(header)  # defines persistent header to send with all API requests

        if mode == "GET":
            r = s.get(url, params=params)

        elif mode == "POST":
            if data:
                r = s.post(url, payload)
            else:
                raise ValueError("POST method chosen but no data was specified")

        elif mode == "PUT":
            if data:
                r = s.put(url, payload)
            else:
                raise ValueError("PUT method chosen but no data was specified")

        elif mode == "DELETE":
            r = s.delete(url)

        else:
            raise ValueError("Invalid API method chosen")

        r_dict = json.loads(r.text)  # loads JSON response into dict

        return {
            "status_code": r.status_code,
            "method": mode,
            "response": r_dict
        }

    def load_mapping(self, endpoint, key, value, api_params=None):  # used for creating a mapping of an endpoint
        """
        :param api_params: additional parameters to pass with api call
        :param endpoint: list an endpoint name as a string (ie. variants, companies, orders)
        :param key: field name within endpoint to be used as key in output dict
        :param value: field name within endpoint to be used as value in output dict
        :return: a dict containing specified keys and values from chosen endpoint

        """

        page = 1
        finished = False
        output = {}

        while not finished:  # loop through until finished due to API pagination
            fixed_params = {
                "limit": 250,
                "page": page
            }

            if api_params:
                params = {
                    **api_params,
                    **fixed_params
                }
            else:
                params = fixed_params

            pass_dict = self.request("GET", endpoint, params=params)

            page += 1  # increment page number for each pass

            if not pass_dict["response"][endpoint]:  # check to see if response is empty to end loop
                finished = True

            for item in pass_dict["response"][endpoint]:
                output[item[key]] = item[value]  # append SKU & ID pair to output dict

        return output

    def load_address(self, company_id):  # returns first address ID for specified company
        params = {
            "company_id": company_id
        }

        add_temp = self.request("GET", "addresses", params=params)

        return add_temp["response"]["addresses"][0]["id"]


class Target:
    def datetime(self, date):
        if len(date.split("/")[2]) == 2:
            dt = datetime.strptime(date, "%m/%d/%y")
        else:
            dt = datetime.strptime(date, "%m/%d/%Y")
        return str(datetime.strftime(dt, "%Y-%m-%d")) + "T12:00:00.000Z"


def import_orders():
    TG = TradeGecko()
    target = Target()

    order_obj = {}

    print("Loading Variant dictionary from TradeGecko")
    prod_dict = TG.load_mapping("variants", "sku", "id")  # load all variants as dict SKU: ID for quick reference

    print("Loading Companies dictionary from TradeGecko (this can take a minute or two)")
    company_dict = TG.load_mapping("companies", "name", "id")  # load all companies as dict NAME: ID for quick reference
    # TODO TradeGecko doesn't provide very good filtering options, a quicker way (without DB) to do this would be good



    #TODO Make it so that the program takes a CSV file from a copy and paste then stores that into a variable which is then used. This is so that the program doesn't do a hard coded look at the a CSV and is based on what you entered in.
    print("Loading Orders from Target CSV file")

    #Assign input to a variable which would be opened later
    #orderFile = input("Enter the file path to the CSV file: ")
    #with open("target.csv") as f:
    #with open(orderFile) as f:
    with open("Target Test POs - Bulk.csv") as f:
        records = csv.DictReader(f)

        for row in records:

            if row["Record Type"] == "H":  # lines where Record Type = "H" are header lines with company details

                if row["Buying Party Name"] not in company_dict:  # check if Target DC exists, create if not
                    print("Company ({0}) does not exist in TradeGecko, creating...".format(row["Buying Party Name"]))

                    company = {
                        "status": "active",
                        "company_type": "business",
                        "name": row["Buying Party Name"],
                        "default_payment_term_id": 487325
                    }

                    company_temp = TG.request("POST", "companies", data=company)["response"]
                    print(company_temp)

                    company_dict[company_temp["company"]["name"]] = company_temp["company"]["id"]

                    address = {
                        "company_id": company_dict["company"]["id"],
                        "address1": row['Buying Party Address 1'],
                        "address2": row['Buying Party Address 2'],
                        "city": row['Buying Party City'],
                        "state": row['Buying Party State'],
                        "zip_code": row['Buying Party Zip'],
                        "country": row['Buying Party Country']
                    }

                    address_temp = TG.request("POST", "addresses", data=address)["response"]
                


                #You can change the status to either finalized, draft, or active
                order_obj[row["PO Number"]] = {
                    "order_number": row["PO Number"],
                    "issued_at": target.datetime(row["PO Date"]),
                    # Typically the program stops here because it doesn't format the minus signs, best solution is to delete
                    # the first part of the ship date in the CSV file before running this
                    "ship_at": target.datetime(row["Ship Dates"]),
                    "company_id": company_dict[row["Buying Party Name"]],
                    "shipping_address_id": TG.load_address(company_dict[row["Buying Party Name"]]),
                    "status": "draft"
                }

                order_obj[row["PO Number"]]["order_line_items"] = []

            else:  # lines where Record Type = "D" are line items without company details
                if row['Vendor Style']:
                    line_item = {
                        "variant_id": prod_dict[row["Vendor Style"]],
                        "quantity": row["Qty Ordered"],
                        "price": row["Unit Price"],
                        "line_type": "product",
                        "tax_type_id": 455921
                    }

                    order_obj[row["PO Number"]]["order_line_items"].append(line_item.copy())

    print(order_obj)

    for ref in order_obj.keys():
        print("Posting {0} to TradeGecko".format(ref))

        a = TG.request("POST", "orders", data=order_obj[ref])

        order_id = a["response"]["order"]["id"]

        line_count = 1

        line_ids = []

        for item in order_obj[ref]["order_line_items"]:
            item["order_id"] = order_id

            a = TG.request("POST", "order_line_items", data=item)
            line_count += 1

            if a["status_code"] == 201:
                print("Successfully posted line {0} for order {1}".format(
                    line_count,
                    ref
                ))

                line_ids.append(
                    {
                        "order_line_item_id": a["response"]["order_line_item"]["id"],
                        "quantity": item["quantity"]
                    }.copy())
        # These lines below essentially make the order become invoiced which is not a good thing
        # print("Invoicing {0}".format(ref))

        # payload = {
        #     "order_id": order_id,
        #     "invoice_line_items": line_ids,
        #     "invoice_number": ref
        # }

        # a = TG.request("POST", "invoices", data={"invoice": payload})
        # print(a)


if __name__ == "__main__":
    try:
        import_orders()

    except Exception as e:
        print("An Error Occurred, please take a screenshot before continuing\n{0}\n".format(e))
        input("Press Enter to Continue...")
        sys.exit(1)

