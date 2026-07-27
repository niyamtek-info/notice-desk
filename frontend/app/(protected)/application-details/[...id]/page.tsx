"use client";

import React from "react";
import ApplicationDetails from "@/components/pages/application-details/ApplicationDetails";
import { useParams } from "next/navigation";

const ApplicationDetailsPage = () => {
    const params = useParams();
    const id = params?.id?.[0] as string;
    const recordId = params?.id?.[1] as string;

    return <ApplicationDetails applicationId={id} recordId={recordId}/>;
};

export default ApplicationDetailsPage;
