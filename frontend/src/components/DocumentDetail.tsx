import { Document } from "../common/types";
import { API } from "aws-amplify";
import { getDateTime } from "../common/utilities";
import { filesize } from "filesize";
import { Link } from "react-router-dom";
import {
  DocumentIcon,
  CircleStackIcon,
  ClockIcon,
  CheckCircleIcon,
  CloudIcon,
  CogIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";

const DocumentDetail: React.FC<Document> = (document: Document) => {
  const deleteDocument = async (documentid) => {
     const deleteDoc = await API.post(
      "serverless-pdf-chat",
      `/doc/delete/${documentid}`,
      {},
    );
  };

  return (
    <>
      <h3 className="text-center mb-3 text-lg font-bold tracking-tight text-gray-900">
      	  <Link
	    to={`/doc/${document.documentid}/${document.conversations[0].conversationid}/`}
            key={document.documentid}
            className="block p-6 bg-white border border-gray-200 rounded hover:bg-gray-100"
           >
           {document.filename}
	   </Link>
      </h3>
      <div className="flex flex-col space-y-2">
        <div className="inline-flex items-center">
          <DocumentIcon className="w-4 h-4 mr-2" />
          {document.pages} pages
        </div>
        <div className="inline-flex items-center">
          <CircleStackIcon className="w-4 h-4 mr-2" />
          {filesize(Number(document.filesize)).toString()}
        </div>
        <div className="inline-flex items-center">
          <ClockIcon className="w-4 h-4 mr-2" />
          {getDateTime(document.created)}
        </div>
        {document.docstatus === "UPLOADED" && (
          <div className="flex flex-row justify-center pt-4">
            <span className="inline-flex items-center self-start bg-gray-100 text-gray-800 text-xs font-medium mr-2 px-2.5 py-0.5 rounded">
              <CloudIcon className="w-4 h-4 mr-1" />
              Awaiting processing
            </span>
          </div>
        )}
        {document.docstatus === "PROCESSING" && (
          <div className="flex flex-row justify-center pt-4">
            <span className="inline-flex items-center self-start bg-blue-100 text-blue-800 text-xs font-medium mr-2 px-2.5 py-0.5 rounded">
              <CogIcon className="w-4 h-4 mr-1 animate-spin" />
              Processing document
            </span>
          </div>
        )}
        {document.docstatus === "READY" && (
	<div>
	  <div className="inline-flex items-center">
	      <button
	        onClick={async () => {await deleteDocument(document.documentid)}}
		className="inline-flex items-center hover:bg-gray-200"
		documentid={document.documentid}
	      >
                <TrashIcon className="w-4 h-4 mr-2" />
                Delete
	      </button>

	  </div>
          <div className="flex flex-row justify-center pt-4">
            <span className="inline-flex items-center self-start bg-green-100 text-green-800 text-xs font-medium mr-2 px-2.5 py-0.5 rounded">
              <CheckCircleIcon className="w-4 h-4 mr-1" />
              Ready to chat
            </span>
          </div>
	  </div>
        )}
      </div>
    </>
  );
};

export default DocumentDetail;
