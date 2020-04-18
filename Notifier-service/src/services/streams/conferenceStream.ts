import { Model } from "mongoose";
import { ConferenceModel } from "../../interfaces/models/conference";
import { ConferenceDocument } from "../../schemas/conferences";
import { injectable } from "inversify";
import { Logger } from "../../utility/log";
import { Observable, Observer } from 'rxjs'
import { share } from 'rxjs/operators'

import { ConferenceStream } from "../../interfaces/services/streams/conferenceStream";


@injectable()
export class ConferenceStreamMongo extends ConferenceStream {

    private logger = new Logger(this.constructor.name).getLogger()
    private streamObs$: Observable<any>
    constructor(conferenceModel: ConferenceModel) {
        super(conferenceModel)
        this.logger.info("Conference Stream started")
        let changeStream = conferenceModel.makeQuery(async (model: Model<ConferenceDocument, {}>) => {
            try {
                let stream = await model.watch([] , {fullDocument: 'updateLookup'});
                return Promise.resolve(stream)
            } catch (err) {
                this.logger.error(`Failed to get a watch stream :${err}`)
                return Promise.reject(err)
            }
        })

        this.streamObs$ = Observable.create((observer: Observer<any>) => {
            changeStream.then(stream => {
                stream.on("change", (data:Object) => {
                    observer.next(data)
                })
            }).catch(error => {
                this.logger.error(`change stream failed:${error}`)
                observer.error(error)
                observer.complete()
            })
        })
            .pipe(
                share()
            )


    }

    public getStream(): Observable<any> {
        return this.streamObs$;
    }



} 