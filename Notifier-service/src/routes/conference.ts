import { Router , Request , Response } from 'express';
import { ConferenceController } from '../controllers/conference';
import { Conference } from '../schemas/conferences';
import { Route } from '../interfaces/route';
import { injectable } from 'inversify';


/**
 * Conference Route attaches the Conference controller
 * and handlers to the routes defined
 * @export
 * @class ConferenceRoute
 * @extends {Route}
 */

@injectable()
export class ConferenceRoute extends Route{

    protected routeName:string;
    constructor(private controller: ConferenceController){
        super(controller)
        this.routeName = "conferences" ;
        this.setRoutes()
    }

    /**
     * Routes for Conference routes 
     * base route : /conferences
     * 
     * - /getOne returns one conference data
     * - /:offset/:count (offset[int], count[int]) , returns several conferences , on bad argument returns empty payload
     * - /:category/:offset/:count (category[string] , offset[int], count[int]) , returns several conferences , on bad argument returns empty payload
     * - /:categories , returns list of categories, returns null payload on fail
     * @protected
     * @memberof ConferenceRoute
     */
    protected setRoutes(){
        this.router.get("/getone",this.controller.getOne)
        this.router.get("/:offset/:count" , this.controller.getConferences)
        this.router.get("/:category/:offset/:count" , this.controller.getConferencesFomCategory)
        this.router.get("/categories" , this.controller.getCategories)
    }
    
} 