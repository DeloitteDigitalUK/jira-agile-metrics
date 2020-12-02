import sys
import logging
from datetime import datetime, date
from trello import TrelloApi
import requests


logger = logging.getLogger(__name__)


class JiraLikeIssue(object):
    def __init__(self, key, url, fields, history):
        self.key = key
        self.url = url
        self.id = key
        self.fields = fields
        self.changelog = Changelog(history)


class Changelog(object):
    def __init__(self, history):
        self.histories = []
        if history is not None:
            self.histories.append(history)

    def append(self, history):
        self.histories.append(history)

    def sort(self):
        self.histories.sort(key=lambda x: x.created)


class JiraLikeHistory(object):
    def __init__(self, created, item):
        self.items = [item]
        self.created = created


class JiraLikeHistoryItem(object):
    def __init__(self, field, fromString, toString):

        self.field = field
        self.fromString = fromString
        self.toString = toString


class JiraLikeField(object):
    def __init__(self, name):

        self.name = name


class JiraLikeFields(object):
    def __init__(
        self,
        labels,
        summary,
        status,
        created,
        issuetype=JiraLikeField("card"),
        resolution=JiraLikeField("na"),
    ):

        self.labels = labels
        self.summary = summary
        self.status = status
        self.created = created
        self.issuetype = issuetype
        self.resolution = resolution


class TrelloClient(object):
    """
    Wrapper around the Trello API exposing methods that match
    those provided by the JIRA client
    """

    def __init__(
        self, member, key, token, type_mapping=None, flagged_mapping=None
    ):

        self.member = member
        self.key = key
        self.token = token
        self.type_mapping = type_mapping
        self.flagged_mapping = flagged_mapping

        self.trello = TrelloApi(self.key, token=self.token)

        self.boards = self.trello.members.get_board(self.member)

        self.from_date = datetime.strptime("2010-01-01", "%Y-%m-%d")

    def fields(self):
        return [
            {"id": "status", "name": "status"},
            {"id": "Flagged", "name": "Flagged"},
        ]

    def search_issues(self, board_name, expand=False, maxResults=None):
        issues = None
        for board in self.boards:
            if board["name"] == board_name:
                issues = self.issues_from_board_actions(board)
                break
        return issues

    def issues_from_board_actions(self, board):
        """
        Get all the work items in a boards history of actions
        """
        actions = []
        limit = 1000
        filter = [
            "createCard",
            "updateCard",
            "moveCardToBoard",
            "moveCardFromBoard",
            "copyCard",
            "copyCommentCard",
        ]
        before = None

        _work_items = []

        while (before is None) or (before > self.from_date.date()):
            while True:
                try:
                    batch = self.trello.boards.get_action(
                        board["id"], limit=limit, filter=filter, before=before
                    )
                    break
                except requests.exceptions.HTTPError as exception:
                    logger.error(f"get action from trello failed:{exception}")

            actions.extend(batch)
            if len(batch) > 0:
                id_time = int(batch[-1]["id"][0:8], 16)
                before = date.fromtimestamp(id_time)
            else:
                break

        logger.info(f"{board['name']} has {str(len(actions))} actions.")

        for index, action in enumerate(actions):
            try:
                card_id = action["data"]["card"]["id"]
            except KeyError:
                continue

            work_item = next(
                (
                    work_item
                    for work_item in _work_items
                    if work_item.id == card_id
                ),
                None,
            )

            state_transition = self.state_transition(action)

            if work_item is not None:
                if state_transition is not None:
                    work_item.changelog.append(state_transition)
                    work_item.changelog.sort()

            else:
                while True:
                    try:
                        card = self.trello.cards.get(card_id)
                        break
                    except requests.exceptions.HTTPError as exception:
                        if exception.response.status_code == 404:
                            sys.stdout.write("_")
                            sys.stdout.flush()
                            card = None
                            break
                        logger.error(
                            f"get cards from trello failed:{exception}"
                        )

                if card is not None:
                    date_created = datetime.fromtimestamp(
                        int(card["id"][0:8], 16)
                    ).strftime("%m/%d/%Y, %H:%M:%S")
                    while True:
                        try:
                            card_list = self.trello.lists.get(card["idList"])
                            break
                        except requests.exceptions.HTTPError as exception:
                            logger.error(
                                f"get lists from trello failed:{exception}"
                            )

                    labels = []

                    issuetype = "card"
                    for label in card["labels"]:
                        clean_label = label["name"].lower().strip()
                        if self.type_mapping is not None:
                            for mapping in self.type_mapping:
                                if clean_label in self.type_mapping[mapping]:
                                    issuetype = mapping
                            labels.append(clean_label)

                    work_item = JiraLikeIssue(
                        key=card_id,
                        url=card["url"],
                        fields=JiraLikeFields(
                            labels=labels,
                            summary=card["name"],
                            status=JiraLikeField(card_list["name"]),
                            created=date_created,
                            issuetype=JiraLikeField(issuetype),
                        ),
                        history=state_transition,
                    )

                    _work_items.append(work_item)

            logger.info(f"processed action {index} of {len(actions)}")

        return _work_items

    def state_transition(self, action):
        """
        Get a state transition from an action
        """

        while True:
            try:
                if action["type"] == "updateCard":
                    if "listAfter" in action["data"]:
                        to_state = action["data"]["listAfter"]["name"]
                    else:
                        return None
                    from_state = action["data"]["listBefore"]["name"]
                    break
                elif action["type"] == "moveCardToBoard":
                    list_details = self.trello.lists.get(
                        action["data"]["list"]["id"]
                    )
                    to_state = list_details["name"]
                    from_state = "undefined"
                    break
                elif action["type"] == "moveCardFromBoard":
                    to_state = "undefined"
                    list_details = self.trello.lists.get(
                        action["data"]["list"]["id"]
                    )
                    from_state = list_details["name"]
                    break
                elif action["type"] == "createCard":
                    from_state = "CREATED"
                    list_details = self.trello.lists.get(
                        action["data"]["list"]["id"]
                    )
                    to_state = list_details["name"]
                    break
                elif action["type"] in [
                    "addAttachmentToCard",
                    "commentCard",
                    "addMemberToCard",
                    "updateCheckItemStateOnCard",
                    "addChecklistToCard",
                    "removeMemberFromCard",
                    "deleteCard",
                    "deleteAttachmentFromCard",
                    "removeChecklistFromCard",
                ]:
                    # Do we want to do something different with deleteCard?
                    return None
                elif action["type"] in ["copyCard", "copyCommentCard"]:
                    # Grab history from previous card and add it to this one?
                    return None
                else:
                    logger.info(f"Found Action Type:{action['type']}")
                    return None
            except requests.exceptions.HTTPError as exception:
                logger.error(f"get lists from trello failed:{exception}")

        state_transition = JiraLikeHistory(
            action["date"],
            JiraLikeHistoryItem(
                field="status", fromString=from_state, toString=to_state
            ),
        )

        return state_transition
