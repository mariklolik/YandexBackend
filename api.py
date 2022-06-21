import flask
import sqlalchemy
from dbremote.db_session import create_session, global_init
from flask import Flask, request, jsonify, Blueprint, Response, abort
from dbremote.category import Category
from datetime import datetime
import json


def datetime_valid(dt_str):
    try:
        datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return False
    return True


global_init("db/data.sqlite")
blueprint = Blueprint('api', __name__)


@blueprint.route("/imports", methods=["POST", "GET"])
def add_to_db():
    session = create_session()

    content = request.json

    abstract = {'id': '',
                'parentId': '',
                'name': '',
                'price': -1,
                'updateDate': '',
                'type': '',
                'latest': True}

    updateDate = content['updateDate']

    if not datetime_valid(updateDate):
        print("not valid time")
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    updateDate = datetime.fromisoformat(updateDate.replace("Z", "+00:00"))

    abstract['updateDate'] = updateDate
    # print(abstract['updateDate'], type(abstract['updateDate']))
    for item in content["items"]:
        for value in item:
            if value not in abstract.keys():
                print(f"{value} not in allowed values")
                return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
            abstract[value] = item[value]
        new_item = Category()
        old_item = session.query(Category).filter(Category.id == abstract['id'], Category.latest == True).first()
        if old_item:
            old_item.latest = False

        new_item.id = abstract['id']
        new_item.parentId = abstract['parentId']
        new_item.name = abstract['name']
        new_item.price = abstract['price']
        new_item.updateDate = abstract['updateDate']
        new_item.type = abstract['type']
        new_item.latest = abstract['latest']
        new_item.date = abstract['updateDate']
        # print(new_item.date)
        session.add(new_item)

    session.commit()
    return Response(status=200)


def get_children(root: Category, session):
    if root.type == 'OFFER' and root.latest == True:
        return root
    children = session.query(Category).filter(Category.parentId == root.id, Category.latest == True)
    res = []
    for i in children:
        res.append(get_children(i, session))

    res2 = [root, *res]
    return res2


def children_to_json(children: list):
    abstract = {'id': '',
                'parentId': '',
                'name': '',
                'price': -1,
                'type': '',
                'latest': True,
                'date': ''}
    for i in range(len(children)):
        if type(children[i]) == list:
            children_to_json(children[i])
        else:
            abstract['id'] = children[i].id
            abstract['parentId'] = children[i].parentId
            abstract['name'] = children[i].name
            abstract['price'] = children[i].price
            abstract['date'] = datetime.isoformat(children[i].date)
            abstract['latest'] = children[i].latest
            abstract['type'] = children[i].type
            children[i] = abstract.copy()

def get_price(children):
    n = 0
    for i in range(len(children)):
        if type(children[i]) == list:
            n += get_price(children[i])
        else:
            if (children[i].price != -1):
                n += children[i].price
    return n


def delete_children(children: list, session):
    for i in range(len(children)):
        if type(children[i]) == list:
            delete_children(children[i], session)
        else:
            old = session.query(Category).filter(Category.id == children[i].id)
            for olds in old:
                session.delete(olds)

def form_dict(children):
    if children['type'] == "OFFER":
        return children
    child = []
    abstract = {'id': '',
                'parentId': '',
                'name': '',
                'price': -1,
                'type': '',
                'latest': True,
                'date': ''}

@blueprint.route("/delete/<string:id>", methods=["DELETE", "GET"])
def delete_item(id: str):
    session = create_session()

    elements = session.query(Category).filter(Category.id == id)

    old = elements.filter(Category.latest == 0)

    latest = elements.filter(Category.latest == 1).first()
    if latest == None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404

    # delete old
    for i in old:
        session.delete(i)

    children = get_children(latest, session)
    delete_children(children, session)
    # children_to_json(children)
    session.commit()
    return Response(status=200)


@blueprint.route("/nodes/<string:id>", methods=["GET", "POST"])
def info(id: str):
    session = create_session()
    element = session.query(Category).filter(Category.id == id, Category.latest == True).first()
    if element == None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404
    children = get_children(element, session)
    n = get_price(children)
    print(children, n)
    children_to_json(children)
    #print(children)
    return json.dumps(children)
