import sqlite_utils
import datetime
from sqlite_utils.db import NotFoundError
import git
import json


def iterate_file_versions(repo_path, subdir, filepath, ref="main"):
    repo = git.Repo(repo_path, odbt=git.GitDB)
    
    commits = reversed(list(repo.iter_commits(ref, paths=subdir)))
    for commit in commits:
        # sub directories basically...    
        for tree in commit.tree.trees:
            for b in tree.blobs:

                if b.name == filepath:
                
                    yield commit.committed_datetime, commit.hexsha, b.data_stream.read()


def create_tables(db):
    db["snapshots"].create(
        {
            "id": int,  # Will be 1, 2, 3 based on order - for nice sorting
            "title": str,  # Human readable date, for display purposes
            "hash": str,
            "when": int,
        },
        pk="id",
    )
    db["snapshots"].create_index(["hash"], unique=True)
    
    db["hospital_snapshot"].create(
        {
            "id": str,      # epoch:OBJECTID  -- this may have to change
            "OBJECTID": int,        # I'm not sure if this is unique, or just part of the arcgis
            "snapshotTime": int,
            "Community Name": str,
            "Facility Name": str,
            "Lat": str,
            "Long": str,
            "Emergency Department Availability": str,
            "Percentage of Time Open (2015)": str,
            "Nearest Alternate Emergency Department": str,
            "Acute Care Availability": str,
            "Acute Care Number of Beds": int,
            "Acute Care Occupancy Rate (2015-16)": str,
            "Transitional Care Occupancy Rate (2015-16)": str,
            "Transitional Care Availability": str,
            "Transitional Care Number of Beds": int,
            "Transitional Care Occupancy Rate (2015-16)": int,
            "Diagnostic Care Services Available": str,
            "Emergency Medical Services Station": str,
            "Nearest Alternate Emergency Medical Services Station": str,
            "Personal Care Home": str,
            "Personal Care Home Number of Beds": int,
            "geometry_x": int,
            "geometry_y": int,
         },
         pk="id",
         
    )
    # db["outage_snapshots"].create(
    #     {
    #         "id": str,
    #         "outage": int,
    #         "snapshot": int,
    #         "lastUpdateTime": int,
    #         "currentEtor": int,
    #         "autoEtor": int,
    #         "estCustAffected": int,
    #         "hazardFlag": int,
    #         "latitude": str,
    #         "longitude": str,
    #         "regionName": int,
    #         "cause": int,
    #         "crewCurrentStatus": int,
    #     },
    #     pk="id",
    #     foreign_keys=("regionName", "snapshot", "outage", "crewCurrentStatus", "cause"),
    # )


def save_hospital_snapshot(db, snapshot, when, hash, lookup):
    # If outage does not exist, save it first
    
    data = dict()
    
    for field, value in snapshot.get('attributes').items():
        data[lookup.get(field)] = value
    
    
    data['geometry_x'] = snapshot.get('geometry').get('x')
    data['geometry_y'] = snapshot.get('geometry').get('y')
    
    
    try:
        snapshot_id = list(db["snapshots"].rows_where("hash = ?", [hash]))[0]["id"]
    except IndexError:
        snapshot_id = (
            db["snapshots"]
            .insert(
                {
                    "hash": hash,
                    "title": str(when),
                    "when": int(datetime.datetime.timestamp(when)),
                }
            )
            .last_pk
        )
    # this should probably check to see if any data changed, so I don't need to insert another row if it hasn't
    # this will run if any row has changed
    # do a fetch without date to see if data is the same, 
    if not row_exists(db["hospital_snapshot"], data):
        data['snapshotTime'] = when
        data['id'] = "{}:{}".format(int(datetime.datetime.timestamp(when)), data['OBJECTID'])
        # upsert probably isn't needed since we check already
        db["hospital_snapshot"].upsert(data, pk="id")        # will insert if objectid is diff
        
    
def row_exists(table, data):
    """
    checks to see if data exists in table
    """
    where = list()
    values = list()
    wherestr = ""
    for field, value in data.items():
        if value is None:
            where.append(f'"{field}" IS NULL')
        else:
            where.append(f'"{field}"=?')
            values.append(value)
            wherestr += f'"{field}"="{value}" AND '

    for row in table.rows_where(" AND ".join(where), values):
        return True
    
    return False

def create_field_lookup(fields):
    """
    returns lookup dict for fields (since name is cutoff, but alias has whole thing, like wtf)
    """
    lookup = dict()
    for field in fields:
        lookup[field.get('name')] = field.get('alias')
    
    return lookup

if __name__ == "__main__":
    import sys

    db_name = sys.argv[-1]
    assert db_name.endswith(".db")
    db = sqlite_utils.Database(db_name)
    if not db.tables:
        create_tables(db)
    last_commit_hash = None
    try:
        last_commit_hash = db.conn.execute(
            "select hash from snapshots order by id desc limit 1"
        ).fetchall()[0][0]
        ref = "{}..HEAD".format(last_commit_hash)
    except IndexError:
        ref = None

    # testing
    
    
    # this is from repo root
    # TODO use __file__ so it doesn't matter where we run from...
    # TODO: use named parameters...
    it = iterate_file_versions("..", "rural_health_care_facilities", "rural.json", ref)
    count = 0
    
    for i, (when, hash, data) in enumerate(it):
        count += 1
        if count % 10 == 0:
            print(count, sep=" ", end=" ")
        
        obj = json.loads(data)
        
        field_lookup = create_field_lookup(obj.get('fields'))
        #print(f"when={type(when)}")
        # testing
        
        when = when.replace(hour=2)
        for snapshot in obj.get('features'):
            # these should use named parameters
            save_hospital_snapshot(db, snapshot, when, hash, field_lookup)


   