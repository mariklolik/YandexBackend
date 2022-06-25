from dbremote.db_session import create_session, global_init
from flask import request, Blueprint, Response
from dbremote.category import CategoryOld, CategoryActual
from sqlalchemy import Table, MetaData
from datetime import datetime, timedelta
import json
from copy import copy

global_init("db/data.sqlite")
blueprint = Blueprint('api', __name__)


def datetime_valid(dt_str):
    try:
        datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return False
    return True


def ItemInActual(id: str):
    session = create_session()
    Item = session.query(CategoryActual).filter(CategoryActual.id == id).first()
    return Item != None


def update(id: str, NewData: dict, UpdateDate):
    session = create_session()
    ActualItem = session.query(CategoryActual).filter(CategoryActual.id == id).first()  # Fetching actual item
    ActualItemJSON = copy(ActualItem.__dict__)
    del ActualItemJSON['_sa_instance_state']
    del ActualItemJSON['numericid']  # Auto-increment
    OldItem = CategoryOld(**ActualItemJSON)  # Making a copy with another class
    session.add(OldItem)  # Push to old
    session.delete(ActualItem)  # Item not in actual table any more
    NewData['date'] = UpdateDate
    NewItem = CategoryActual(**NewData)
    session.add(NewItem)  # To actual table
    session.commit()


def GetSubtree(id, session=None):
    if (session == None):
        session = create_session()
    Item = session.query(CategoryActual).filter(CategoryActual.id == id).first()
    if Item.type == "OFFER":
        return Item
    Leaves = session.query(CategoryActual).filter(CategoryActual.parentId == id)
    result = []
    for i in Leaves:
        result.append(GetSubtree(i.id, session))
    return [Item, *result]


def GetParents(id):
    session = create_session()
    Item = session.query(CategoryActual).filter(CategoryActual.id == id).first()
    ItemParent = session.query(CategoryActual).filter(CategoryActual.id == Item.parentId).first()
    parents = []
    while (ItemParent != None):
        parents.append(copy(ItemParent))
        ItemParent = session.query(CategoryActual).filter(CategoryActual.id == ItemParent.parentId).first()
    return parents


def GetPrice(CategoryId):
    session = create_session()
    CategoryItem = session.query(CategoryActual).filter(CategoryActual.id == CategoryId).first()
    if CategoryItem == None:
        return 0
    price = 0
    children_counter = 0
    CategoryLeaves = GetSubtree(CategoryItem.id)
    if type(CategoryLeaves) != list:
        return CategoryLeaves.price, 1
    for SubObject in CategoryLeaves:
        if type(SubObject) == list:  # SubObject is also a tree
            price, children_counter = price + GetPrice(SubObject[0].id)[0], children_counter + \
                                      GetPrice(SubObject[0].id)[1]  # 0 element of subtree is the father-node
        else:
            if (SubObject.type == "OFFER"):
                price += SubObject.price
                children_counter += 1
    return price, children_counter


def UpdateLeavesDate(Leaves, NewDate):
    for i in Leaves:
        if type(i) == list:
            UpdateLeavesDate(i, NewDate)
        else:
            Ijson = copy(i.__dict__)
            del Ijson['_sa_instance_state']
            Ijson['date'] = NewDate
            update(i.id, Ijson, NewDate)


def AddToDataBase(Data: dict):
    session = create_session()
    NewItem = CategoryActual(**Data)
    session.add(NewItem)
    session.commit()


@blueprint.route("/imports/", methods=["POST", "GET"])
def imports_function():
    FetchedData = request.json

    UpdateDate = FetchedData['updateDate']

    if not datetime_valid(UpdateDate):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400

    UpdateDate = datetime.fromisoformat(UpdateDate.replace("Z", "+00:00"))

    for item in FetchedData['items']:
        if ItemInActual(item['id']):
            update(item['id'], item, UpdateDate)

            Leaves = [GetSubtree(item['id'])]
            UpdateLeavesDate(Leaves, UpdateDate)

            # for i in Leaves:
            #     LeaveData = i.__dict__
            #     del LeaveData['_sa_instance_state']  # Removing extra orm-data
            #     update(i.id, LeaveData, UpdateDate)

            Parents = GetParents(item['id'])
            for i in Parents:
                ParentData = i.__dict__
                del ParentData['_sa_instance_state']
                Fullprice, Offercounter = GetPrice(i.id)
                if Offercounter != 0:
                    NewParentPrice = (Fullprice) // Offercounter
                else:
                    NewParentPrice = 0
                ParentData['price'] = NewParentPrice
                update(i.id, ParentData, UpdateDate)
        else:
            item['date'] = UpdateDate
            AddToDataBase(item)
            Fullprice, Offercounter = GetPrice(item['id'])
            if Offercounter != 0:
                item['price'] = (Fullprice) // Offercounter
            else:
                item['price'] = 0
            update(item['id'], item, UpdateDate)
            Parents = GetParents(item['id'])
            for i in Parents:
                ParentData = copy(i.__dict__)
                del ParentData['_sa_instance_state']
                Fullprice, Offercounter = GetPrice(ParentData['id'])
                if Offercounter != 0:
                    NewParentPrice = (Fullprice) // Offercounter
                else:
                    NewParentPrice = 0
                ParentData['price'] = NewParentPrice
                update(i.id, ParentData, UpdateDate)

    return Response(status=200)


def DeleteSubtree(Leaves, session):
    for i in Leaves:
        if type(i) == list:
            DeleteSubtree(i, session)
        else:
            OldCopies = session.query(CategoryOld).filter(CategoryOld.id == i.id).all()
            for old in OldCopies:
                session.delete(old)
            session.delete(i)


@blueprint.route("/delete/<string:id>", methods=["DELETE", "GET"])
def delete_item(id: str):
    session = create_session()

    Item = session.query(CategoryActual).filter(CategoryActual.id == id).first()

    if Item == None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404

    Parents = GetParents(Item.id)
    Leaves = [GetSubtree(id, session)]
    DeleteSubtree(Leaves, session)
    session.commit()
    for i in Parents:
        ParentData = i.__dict__
        del ParentData['_sa_instance_state']
        Fullprice, Offercounter = GetPrice(i.id)
        if Offercounter != 0:
            NewParentPrice = (Fullprice) // Offercounter
        else:
            NewParentPrice = 0
        ParentData['price'] = NewParentPrice
        update(i.id, ParentData, ParentData['date'])

    session.commit()
    return Response(status=200)
