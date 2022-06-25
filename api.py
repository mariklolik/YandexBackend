from dbremote.db_session import create_session, global_init
from flask import request, Blueprint, Response
from dbremote.category import Category
from datetime import datetime, timedelta
import json
from copy import copy


def datetime_valid(dt_str):
    try:
        datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return False
    return True


global_init("db/data.sqlite")
blueprint = Blueprint('api', __name__)


# @blueprint.route("/imports", methods=["POST", "GET"])
# def add_to_db():
#     session = create_session()
#
#     content = request.json
#     # print(content)
#     abstract = {'id': '',
#                 'parentId': '',
#                 'name': '',
#                 'price': -1,
#                 'updateDate': '',
#                 'type': '',
#                 'latest': True}
#
#     updateDate = content['updateDate']
#
#     if not datetime_valid(updateDate):
#         print("not valid time")
#         return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
#     updateDate = datetime.fromisoformat(updateDate.replace("Z", "+00:00"))
#
#     abstract['updateDate'] = updateDate
#     # print(abstract['updateDate'], type(abstract['updateDate']))
#     for item in content["items"]:
#         abstract['id'] = ''
#         abstract['parentId'] = None
#         abstract['name'] = ''
#         abstract['price'] = -1
#         abstract['type'] = ''
#         for value in item:
#             if value not in abstract.keys():
#                 print(f"{value} not in allowed values")
#                 return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
#             abstract[value] = item[value]
#         new_item = Category()
#         old_item = session.query(Category).filter(Category.id == abstract['id'], Category.latest == True)
#         if old_item:
#             # new_item = old_item
#             for i in old_item:
#                 i.latest = False
#
#         new_item.id = abstract['id']
#         new_item.parentId = abstract['parentId']
#         new_item.name = abstract['name']
#         new_item.price = abstract['price']
#         new_item.updateDate = abstract['updateDate']
#         new_item.type = abstract['type']
#         new_item.latest = abstract['latest']
#         new_item.date = abstract['updateDate']
#         # print(new_item.date)
#         if new_item.parentId != None:
#             new_copy = copy(new_item)
#             parent = session.query(Category).filter(Category.id == new_copy.parentId, Category.latest == True).first()
#             if (parent != None):
#                 while (parent.parentId != None):
#                     parent.date = abstract['updateDate']
#                     parent.latest = True
#                     parent = session.query(Category).filter(Category.id == parent.parentId).first()
#                 parent.date = abstract['updateDate']
#                 parent.latest = True
#
#         session.add(new_item)
#
#     session.commit()
#     return Response(status=200)
#
#
# def update_date(root, session, new_date):
#     elems = session.query(Category).filter(Category.parentId == root.id)
#     for i in elems:
#         if i.type == "CATEGORY":
#             update_date(i, session, new_date)
#
#
# def get_children(root: Category, session):
#     if root.type == 'OFFER' and root.latest == True:
#         return root
#     children = session.query(Category).filter(Category.parentId == root.id, Category.latest == True)
#     res = []
#     for i in children:
#         res.append(get_children(i, session))
#
#     res2 = [root, *res]
#     return res2
#
#
# def children_to_json(children: list):
#     abstract = {'id': '',
#                 'parentId': '',
#                 'name': '',
#                 'price': -1,
#                 'type': '',
#                 'latest': True,
#                 'date': ''}
#     for i in range(len(children)):
#         if type(children[i]) == list:
#             children_to_json(children[i])
#         else:
#             abstract['id'] = children[i].id
#             abstract['parentId'] = children[i].parentId
#             abstract['name'] = children[i].name
#             abstract['price'] = children[i].price
#             abstract['date'] = datetime.isoformat(children[i].date)
#             abstract['latest'] = children[i].latest
#             abstract['type'] = children[i].type
#             children[i] = abstract.copy()
#
#
# def item_to_dict(item):
#     abstract = {'id': item.id, 'parentId': item.parentId, 'name': item.name, 'price': item.price,
#                 'date': item.date.strftime("%Y-%m-%dT%H:%M:%S.000Z"), 'type': item.type}
#     return abstract
#
#
# def get_price(children):
#     n = 0
#     for i in range(len(children)):
#         if type(children[i]) == list:
#             n += get_price(children[i])
#         else:
#             if (children[i].price != -1):
#                 n += children[i].price
#     return n
#
#
# def delete_children(children: list, session):
#     for i in range(len(children)):
#         if type(children[i]) == list:
#             delete_children(children[i], session)
#         else:
#             old = session.query(Category).filter(Category.id == children[i].id)
#             for olds in old:
#                 session.delete(olds)
#
#
# def form_dict(children):
#     abstract = {'id': children[0].id, 'parentId': children[0].parentId, 'name': children[0].name,
#                 'price': children[0].price, 'type': children[0].type,
#                 'date': (children[0].date).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
#                 'children': []}
#     n = 0
#     for i in range(1, len(children)):
#         if type(children[i]) == list:
#             res, num, price = form_dict(children[i])
#             abstract['children'].append(res)
#             abstract['price'] += price
#             n += num
#
#         else:
#             abstract2 = {'id': children[i].id, 'parentId': children[i].parentId, 'name': children[i].name,
#                          'price': children[i].price, 'type': children[i].type,
#                          'date': (children[i].date).strftime("%Y-%m-%dT%H:%M:%S.000Z"), 'children': None}
#             abstract['children'].append(abstract2)
#             if abstract['price'] != -1:
#                 abstract['price'] += abstract2['price']
#             else:
#                 abstract['price'] = abstract2['price']
#             n += 1
#     price = abstract['price']
#     if n != 0:
#         abstract['price'] = (abstract['price'] + 1) // n
#     else:
#         abstract['price'] = 0
#     if abstract['children'] == []:
#         abstract['children'] = None
#     return abstract, n, price
#
#
# @blueprint.route("/delete/<string:id>", methods=["DELETE", "GET"])
# def delete_item(id: str):
#     session = create_session()
#
#     elements = session.query(Category).filter(Category.id == id)
#
#     old = elements.filter(Category.latest == 0)
#
#     latest = elements.filter(Category.latest == 1).first()
#     if latest == None:
#         return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404
#
#     # delete old
#     for i in old:
#         session.delete(i)
#
#     children = get_children(latest, session)
#     delete_children(children, session)
#     # children_to_json(children)
#     session.commit()
#     return Response(status=200)
#
#
# @blueprint.route("/nodes/<string:id>", methods=["GET", "POST"])
# def info(id: str):
#     session = create_session()
#     if len(id) != 36:
#         return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
#     element = session.query(Category).filter(Category.id == id, Category.latest == True).first()
#     if element == None:
#         return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404
#
#     children = get_children(element, session)
#
#     ans, num, price = form_dict(children)
#
#     return json.dumps(ans)
#
#
# @blueprint.route("/sales", methods=["GET", "POST"])
# def sales():
#     session = create_session()
#     content = request.args
#     date = content.get('date')
#     if not datetime_valid(date):
#         print("not valid time")
#         return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
#     date = datetime.fromisoformat(date.replace("Z", "+00:00"))
#
#     data = session.query(Category).filter(Category.type == "OFFER", Category.date <= date,
#                                           Category.date >= date - timedelta(days=1)).all()
#
#     ans = {'items': []}
#     for item in data:
#         ans['items'].append(item_to_dict(item))
#     if ans['items'] == []:
#         ans['items'] = None
#
#     return json.dumps(ans)
#
#
# # @blueprint.route("/node/<string:id>/statistic/", methods=["GET", "POST"])
# # def stats(id):
# #     session = create_session()
# #     content = request.args
# #     item_id = id
# #
# #     date_start = content.get('dateStart')
# #     if not datetime_valid(date_start):
# #         print("not valid time")
# #         return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
# #     date_start = datetime.fromisoformat(date_start.replace("Z", "+00:00"))
# #
# #     date_end = content.get('dateEnd')
# #     if not datetime_valid(date_end):
# #         print("not valid time")
# #         return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
# #     date_end = datetime.fromisoformat(date_end.replace("Z", "+00:00"))
# #
# #     whole_data = session.query(Category).filter(Category.id == item_id, Category.date >= date_start,
# #                                                 Category.date <= date_end).distinct(Category.date)
# #     print(whole_data)
#
#
#     return Response(status=200)
