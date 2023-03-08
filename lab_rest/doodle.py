from typing import List, Dict, Union

from fastapi import FastAPI, Body
from pydantic import BaseModel
from starlette import status
from starlette.responses import JSONResponse

app = FastAPI()


last_poll_id = 1000
last_vote_id = 1000


class DatabasePoll:
    def __init__(self, title: str, options: List[str]):
        global last_poll_id

        self.id: int = last_poll_id
        last_poll_id += 1

        self.title: str = title
        self.options: Dict[int: DatabaseOption] = {index: DatabaseOption(index, option) for index, option in enumerate(options)}
        self.votes: Dict[int: DatabaseVote] = {}

    def add_options(self, options: List[str]):
        options_amount = len(self.options)
        for option in (DatabaseOption(index+options_amount, option) for index, option in enumerate(options)):
            self.options[option.id] = option

    def vote_for_option(self, option_id: int):
        global last_vote_id

        option = self.options.get(option_id)
        if not option:
            return None

        vote = DatabaseVote(option)
        self.votes[vote.id] = vote
        return vote

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "options": list(map(lambda option: option.serialize(), self.options.values())),
            "votes": list(map(lambda vote: vote.serialize(), self.votes.values()))
        }


class DatabaseOption:
    def __init__(self, id: int, content: str):
        self.id: int = id
        self.content: str = content

    def serialize(self):
        return {
            "number": self.id,
            "content": self.content
        }


class DatabaseVote:
    def __init__(self, option: DatabaseOption):
        global last_vote_id

        self.id: int = last_vote_id
        last_vote_id += 1

        self.option: DatabaseOption = option

    def serialize(self):
        return {
            "id": self.id,
            "option_number": self.option.id,
            "option": self.option.content
        }


polls = dict()


class PollRequest(BaseModel):
    title: str
    options: List[str]


class UpdatePollRequest(BaseModel):
    title: Union[str, None]
    options: Union[List[str], None]


@app.get('/poll')
async def get_all_polls():
    return list(map(lambda poll: poll.serialize(), polls.values()))


@app.post('/poll')
async def create_poll(poll_request: PollRequest):
    new_poll = DatabasePoll(poll_request.title, poll_request.options)
    polls[new_poll.id] = new_poll
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=new_poll.serialize())


@app.get('/poll/{poll_id}')
async def get_poll(poll_id: int):
    return polls[poll_id].serialize() if poll_id in polls else JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})


@app.put('/poll/{poll_id}')
async def update_poll(poll_id: int, update_poll_request: UpdatePollRequest):
    if poll_id not in polls:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})

    poll_to_update = polls[poll_id]
    if update_poll_request.title:
        poll_to_update.title = update_poll_request.title

    if update_poll_request.options:
        poll_to_update.options = []
        poll_to_update.votes = []
        poll_to_update.add_options(update_poll_request.options)

    polls[poll_id] = poll_to_update
    return poll_to_update.serialize()


@app.delete('/poll/{poll_id}')
async def delete_poll(poll_id: int):
    if poll_id not in polls:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})

    deleted_poll = polls[poll_id]
    del polls[poll_id]
    return deleted_poll.serialize()


@app.get('/poll/{poll_id}/vote')
async def get_votes(poll_id: int):
    if poll_id not in polls:
        return []
    return list(map(lambda vote: vote.serialize(), polls[poll_id].votes.values()))


@app.post('/poll/{poll_id}/vote')
async def vote(poll_id: int, option_id: int = Body()):
    if poll_id not in polls:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})

    if option_id not in polls[poll_id].options:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=polls[poll_id].vote_for_option(option_id).serialize())


@app.get('/poll/{poll_id}/vote/{vote_id}')
async def get_vote(poll_id: int, vote_id: int):
    return polls[poll_id].votes[vote_id].serialize() if poll_id in polls and vote_id in polls[poll_id].votes else {}


@app.put('/poll/{poll_id}/vote/{vote_id}')
async def update_vote(poll_id: int, vote_id: int, option_id: int = Body()):
    if poll_id in polls and vote_id in polls[poll_id].votes and option_id in polls[poll_id].options:
        polls[poll_id].votes[vote_id].option = polls[poll_id].options[option_id]
        return polls[poll_id].votes[vote_id].serialize()

    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})


@app.delete('/poll/{poll_id}/vote/{vote_id}')
async def remove_vote(poll_id: int, vote_id: int):
    if poll_id in polls and vote_id in polls[poll_id].votes:
        deleted_vote = polls[poll_id].votes[vote_id]
        del polls[poll_id].votes[vote_id]
        return deleted_vote.serialize()

    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
