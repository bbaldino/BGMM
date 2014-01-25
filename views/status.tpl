% include header.tpl {"session_status": session_status}
<div class="container">
    <div class="row">
        <div class="well">
            <div class="row">
                <div class="col-md-5">
                    <a class="btn btn-primary" href="/scan">Scan for new files</a>
                    <a class="btn btn-primary" href="/upload">Upload scanned files</a>
                    <a class="btn btn-primary" href="/sync">Sync with library</a>
                </div>
                <div class="col-md-6">
                    <label for="select" class="col-md-4 control-label">Change selected files' status to:</label>
                    <div class="col-md-3">
                        <select class="form-control" id="select">
                            <option>1</option>
                            <option>2</option>
                            <option>3</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="row">
        <div>
            <table class="table table-bordered table-striped table-hover">
                <thead>
                    <tr>
                        <th></th>
                        <th>Path</th>
                        <th>Status</th>
                        <th>Id</th>
                    </tr>
                </thead>
                <tbody>
                    % for song in songs:
                    <tr>
                        <td>
                            <input type="checkbox" id="{{song.path}}">
                        </td>
                        <td>
                            {{song.path}}
                        </td>
                        <td>
                            {{song.status}}
                        </td>
                        <td>
                            {{song.id}}
                        </td>
                    </tr>
                    % end
                </tbody>
            </table>
        </div>
    </div>
    <div class="row">
        <div style="text-align: center">
            <ul class="pagination">
                % prev_page = curr_page - 1
                % next_page = curr_page + 1
                % if num_pages > 10:
                %   start_page = max(1, curr_page - 5)
                %   end_page = min(num_pages + 1, curr_page + 5)
                % else:
                %   start_page = 1
                %   end_page = num_pages
                % end
                % if curr_page <= 1:
                    <li class="disabled"><span>&laquo;</span></li>
                % else:
                    <li><a href="?page={{prev_page}}">&laquo;</a></li>
                % end
                % if start_page > 1:
                    <li><a href="?page=1">1</a></li>
                % end
                % for page in range(start_page, end_page):
                  % if page == curr_page:
                    <li class="active"><span>{{page}}</span></li>
                  % else:
                    <li><a href="?page={{page}}">{{page}}</a></li>
                  % end
                % end
                % if end_page < num_pages + 1:
                    <li><a href="?page={{num_pages}}">{{num_pages}}</a></li>
                % end
                % if curr_page >= (num_pages + 1):
                    <li class="disabled"><span>&raquo;</span></li>
                % else:
                    <li><a href="?page={{next_page}}">&raquo;</a></li>
                % end
            </ul>
        </div>
    </div>
</div>
