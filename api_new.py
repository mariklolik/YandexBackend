from dbremote.db_session import create_session, global_init
from flask import request, Blueprint, Response
from dbremote.category import CategoryOld, CategoryActual
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


@blueprint.route("/imports", methods=["POST", "GET"])
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


def FormDict(Leaves):
    result = copy(Leaves[0].__dict__)
    del result['_sa_instance_state']
    del result['numericid']
    if result['price'] == 0 and result['type'] == 'CATEGORY':
        result['price'] = None
    result['date'] = result['date'].strftime("%Y-%m-%dT%H:%M:%S.000Z")
    result['children'] = []
    for i in range(1, len(Leaves)):
        if type(Leaves[i]) == list:
            SubTreeJSON = FormDict(Leaves[i])
            result['children'].append(SubTreeJSON)
        else:
            SubTreeJSON = copy(Leaves[i].__dict__)
            del SubTreeJSON['numericid']
            del SubTreeJSON['_sa_instance_state']
            SubTreeJSON['date'] = SubTreeJSON['date'].strftime("%Y-%m-%dT%H:%M:%S.000Z")
            SubTreeJSON['children'] = None
            result['children'].append(SubTreeJSON)

    return result


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


@blueprint.route("/nodes/<string:id>", methods=["GET", "POST"])
def info(id: str):
    session = create_session()
    if len(id) != 36:
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    Item = session.query(CategoryActual).filter(CategoryActual.id == id).first()
    if Item == None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404
    Ans = FormDict(GetSubtree(id, session))
    return json.dumps(Ans)


@blueprint.route("/sales", methods=["GET", "POST"])
def sales():
    session = create_session()
    content = request.args
    date = content.get('date')
    if not datetime_valid(date):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    date = datetime.fromisoformat(date.replace("Z", "+00:00"))

    Items = session.query(CategoryActual).filter(CategoryActual.type == "OFFER", CategoryActual.date <= date,
                                                 CategoryActual.date >= date - timedelta(days=1)).all()
    Ans = {'items': []}
    for item in Items:
        ItemJSON = copy(item.__dict__)
        del ItemJSON['numericid']
        del ItemJSON['_sa_instance_state']
        ItemJSON['date'] = ItemJSON['date'].strftime("%Y-%m-%dT%H:%M:%S.000Z")
        ItemJSON['children'] = None
        Ans['items'].append(ItemJSON)
    if Ans['items'] == []:
        Ans['items'] = None
    session.close()
    return json.dumps(Ans)


def GetLastState(id, timestamp, session):
    AllOldItems = session.query(CategoryOld).filter(CategoryOld.id == id, CategoryOld.date == timestamp)
    MaxOldItem = max(AllOldItems, key=lambda x: x.numericid)

    NewItem = session.query(CategoryActual).filter(CategoryActual.id == id, CategoryActual.date == timestamp).first()
    if NewItem != None:
        Item = NewItem
    else:
        Item = MaxOldItem
    return Item


def GetSubtreeState(id, timestamp, session):
    if (session == None):
        session = create_session()
    Item = GetLastState(id, timestamp, session)
    if Item.type == "OFFER":
        return Item

    LeavesNew = session.query(CategoryActual).filter(CategoryActual.parentId == id,
                                                     CategoryActual.date <= timestamp).all()
    LeavesNewNames = [i.name for i in LeavesNew]
    LeavesOld = session.query(CategoryOld).filter(CategoryOld.parentId, CategoryOld.date <= timestamp).all()
    Leaves = [*LeavesNew]
    for i in LeavesOld:
        Same = [j for j in LeavesOld if j.name == i.name]
        MaxLeave = max(Same, key=lambda x: x.numericid)
        if MaxLeave.name not in LeavesNewNames:
            Leaves.append(MaxLeave)
    Leaves = list(set(Leaves))

    result = []
    for i in Leaves:
        result.append(GetSubtree(i.id, session))
    return [Item, *result]


@blueprint.route("/node/<string:id>/statistic", methods=["GET", "POST"])
def stats(id):
    session = create_session()
    content = request.args

    DateStart = content.get('dateStart')
    if not datetime_valid(DateStart):
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    DateStart = datetime.fromisoformat(DateStart.replace("Z", "+00:00"))

    DateEnd = content.get('dateEnd')
    if not datetime_valid(DateEnd):
        print("not valid time")
        return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400
    DateEnd = datetime.fromisoformat(DateEnd.replace("Z", "+00:00"))

    NewItem = session.query(CategoryActual).filter(CategoryActual.id == id).first()
    if NewItem == None:
        return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404

    Timestamps = list(
        set([i.date for i in session.query(CategoryOld).filter(CategoryOld.id == id, CategoryOld.date >= DateStart,
                                                               CategoryOld.date < DateEnd).all()]))
    Result = {'items': []}
    # print(DateStart, Timestamps, DateEnd)
    for time in Timestamps:
        Item = GetLastState(id, time, session)
        Result['items'].append(FormDict(GetSubtreeState(Item.id, time, session)))
    return json.dumps(Result)
