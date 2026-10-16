"""Text-to-request adapter for Train Ticket; independent of scenario identifiers."""
import re

from baseline_nlp import Scorer, expand, handler_docs, query_toks, ui_context
from .state import U


def intent(action, state):
    a = action.lower()
    if re.search(r'log ?in|sign ?in', a):
        state.role = 'admin' if re.search(r'admin|administrator', a) else 'passenger'
        state.select_identity()
        return 'auth', 'getToken'
    if 'administrator' in a:
        state.role = 'admin'
        state.select_identity()
    regular = state.regular
    if re.search(r'regular|non.high.speed', a):
        regular = True
    elif re.search(r'high.speed|gaotie|dongche', a):
        regular = False
    # Viewing the other order list does not select a different trip for booking.
    # The frontend's order filter starts at trainTypeSelected=1.
    if not ('order' in a and re.search(r'refresh|list|filter', a)):
        state.regular = regular
    order = 'order-other' if regular else 'order'
    travel = 'travel2' if state.regular else 'travel'
    if re.search(r'^register|^create.*account', a):
        state.new_account = True
        state.user, state.account_id = U, U
        return 'user', 'registerUser'
    if state.role == 'admin' and re.search(r'^add|^create', a):
        for words, module, name in [('price configuration', 'admin-basic-info', 'addPrice'),
                                   ('station', 'admin-basic-info', 'addStation'),
                                   ('train type', 'admin-basic-info', 'addTrain'),
                                   ('route', 'admin-route', 'addRoute'),
                                   ('trip', 'admin-travel', 'addTravel')]:
            if words in a and (words != 'route' or 'trip' not in a):
                return module, name
    if state.role == 'admin' and 'all orders' in a:
        return 'admin-order', 'getAllOrders'
    if re.search(r'\brebook\b', a):
        return 'rebook', 'rebook'
    if re.search(r'^book|^reserve|^place.*order', a):
        return ('preserve-other' if state.regular else 'preserve'), 'preserve'
    if re.search(r'^(?:try to )?cancel\b', a):
        return 'cancel', 'cancelTicket'
    if 'refund' in a and re.search(r'ask|how much|calculate', a):
        return 'cancel', 'calculate'
    if re.search(r'^pay\b', a):
        return ('payment' if 'external' in a else 'inside-payment'), 'pay'
    if re.search(r'^collect', a):
        return 'execute', 'collectTicket'
    if re.search(r'enter the station|board the train', a):
        return 'execute', 'executeTicket'
    if 'consignee' in a and re.search(r'change|update|modify', a):
        return 'consign', 'updateConsign'
    if re.search(r'luggage|consignment', a):
        if re.search(r'price|cost', a):
            return 'consign-price', 'getPriceByWeightAndRegion'
        return 'consign', ('findByOrderId' if 'order' in a else 'findByAccountId')
    if re.search(r'assurance|insurance', a):
        return 'assurance', ('getAllAssuranceType' if 'type' in a else 'findAssuranceByOrderId')
    if 'contact' in a:
        return 'contacts', ('createNewContacts' if re.search(r'add|create', a) else 'findContactsByAccountId')
    if re.search(r'food|menu', a):
        return 'food', 'getAllFood'
    if 'order' in a:
        if re.search(r'price|cost', a):
            return order, 'getOrderPrice'
        if re.search(r'list|orders|refresh|filter', a):
            return order, 'queryOrdersForRefresh'
        return order, 'getOrderById'
    if re.search(r'details.*trip|trip.*details|open.*details', a):
        return travel, 'getTripAllDetailInfo'
    if re.search(r'search|cheapest|quickest|fewest|transfer', a):
        for words, name in [('cheapest', 'getByCheapest'), ('quickest', 'getByQuickest'),
                            ('fewest', 'getByMinStation'), ('transfer', 'getTransferResult')]:
            if words in a:
                return 'travel-plan', name
        return travel, 'queryInfo'
    return None, None


def parameters(action, state, enums):
    a = action.lower()
    negative = ' '.join(re.findall(r'\b(?:no|without)\b([^.;]*)', a))
    insurance = bool(re.search(r'assurance|insurance', a)) and not re.search(r'assurance|insurance', negative)
    food = 'food' in a and 'food' not in negative
    luggage = bool(re.search(r'luggage|consignment', a)) and not re.search(r'luggage|consignment', negative)
    weight = re.search(r'(\d+(?:\.\d+)?)\s*kg', a)
    selected = state.last_order
    if 'first order' in a and state.orders:
        selected = state.orders[0].get('id', U)
    elif 'second order' in a and len(state.orders) >= 2:
        selected = state.orders[1].get('id', U)
    first = enums.get('SeatClass.FIRSTCLASS', U)
    second = enums.get('SeatClass.SECONDCLASS', U)
    params = {
        'username': state.user, 'userName': state.user, 'password': '111111',
        'verificationCode': '', 'loginId': state.account_id, 'accountId': state.account_id,
        'userId': state.account_id, 'orderId': selected if selected is not None else U,
        'tripId': state.last_trip, 'contactsId': state.last_contact,
        'seatType': second if 'second-class' in a else first,
        'assurance': 1 if insurance else 0,
        'foodType': (2 if re.search(r'station food|food.*station', a) else 1) if food else 0,
        'consigneeName': 'consignee' if luggage else '',
        'consigneeWeight': float(weight[1]) if weight else U,
        'weight': float(weight[1]) if weight else U,
        'within': bool(re.search(r'within|same region', a)),
        'isWithinRegion': bool(re.search(r'within|same region', a)),
        'enableStateQuery': bool(re.search(r'filter.*paid|paid.*filter|cancelled.*filter|filter.*cancelled', a)),
        'state': enums.get('OrderStatus.CANCEL' if 'cancelled' in a else 'OrderStatus.PAID', U),
        'enableTravelDateQuery': bool(re.search(r'filter.*travel date', a)),
        'enableBoughtDateQuery': bool(re.search(r'filter.*purchase date', a)),
        'date': '2026-10-01', 'departureTime': '2026-10-01', 'travelDate': '2026-10-01',
        'travelDateStart': '2026-09-01' if 'travel date' in a else None,
        'travelDateEnd': '2026-12-31' if 'travel date' in a else None,
        'boughtDateStart': '2026-09-15' if 'purchase date' in a else None,
        'boughtDateEnd': '2026-09-15' if 'purchase date' in a else None,
    }
    places = re.search(r'from ([A-Z][A-Za-z ]+?) to ([A-Z][A-Za-z ]+?)(?: departing|\s*[,.;]|$)', action)
    if places:
        start, end = places.groups()
        params.update(startingPlace=start, endPlace=end, startStation=start, endStation=end,
                      startStationName=start, endStationName=end, **{'from': start, 'to': end})
    return params


class Grounder:
    def __init__(self, project):
        self.project = project
        tokens, self.files, self.ui_sites = ui_context(str(project.root), project.ix)
        self.scorer = Scorer(*handler_docs(project.ix, tokens))
        self.handlers = sorted({mid for mid, _, _ in project.ix.handlers})

    def step(self, action, state):
        module, name = intent(action, state)
        expected = f'ts-{module}-service' if module else None
        scores = {mid: score for score, mid in self.scorer.rank(expand(query_toks(action)))}
        ranked = []
        for mid in self.handlers:
            meta = self.project.methods[mid]
            score = scores.get(mid, 0)
            if expected and meta['module'] == expected and meta['name'] == name:
                score += 10
            elif 'admin' in meta['module'] and state.role != 'admin':
                score *= 0.25
            ranked.append((score, mid))
        ranked.sort(key=lambda p: (-p[0], p[1]))
        params = parameters(action, state, self.project.enums)
        return ranked[0][1], params, {
            'intent': {'module': expected, 'method': name},
            'candidates': [{'method': mid, 'score': score} for score, mid in ranked[:5]],
            'low_confidence': ranked[0][0] < 2 or ranked[0][0] - ranked[1][0] < 0.1,
        }
